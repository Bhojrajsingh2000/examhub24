from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class TestAttempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        AUTO_SUBMITTED = 'auto_submitted', 'Auto Submitted'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='test_attempts')
    test = models.ForeignKey('mock_tests.MockTest', on_delete=models.CASCADE, related_name='attempts')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.IN_PROGRESS)

    total_score = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    correct_count = models.PositiveIntegerField(default=0)
    wrong_count = models.PositiveIntegerField(default=0)
    unattempted_count = models.PositiveIntegerField(default=0)
    accuracy = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['test', '-total_score'], name='idx_attempt_test_score'),
            models.Index(fields=['user', 'status'], name='idx_attempt_user_status'),
        ]

    def __str__(self):
        return f"{self.user} - {self.test.title}"

    def finalize(self, auto_submitted=False):
        """
        Evaluates every AnswerResponse for this attempt, computes the score using the
        test's marking scheme, saves summary stats, and recalculates the rank of every
        completed attempt for this test.
        """
        responses = self.responses.select_related('question').all()

        total_score = Decimal('0')
        correct = wrong = unattempted = 0

        for response in responses:
            question = response.question
            if not response.selected_option:
                unattempted += 1
                response.is_correct = None
                response.marks_awarded = Decimal('0')
            elif response.selected_option == question.correct_option:
                correct += 1
                response.is_correct = True
                response.marks_awarded = question.marks
                total_score += question.marks
            else:
                wrong += 1
                response.is_correct = False
                if self.test.negative_marking:
                    response.marks_awarded = -question.negative_marks
                    total_score += -question.negative_marks
                else:
                    response.marks_awarded = Decimal('0')
            response.save(update_fields=['is_correct', 'marks_awarded'])

        attempted = correct + wrong
        accuracy = (Decimal(correct) / Decimal(attempted) * 100) if attempted else Decimal('0')

        self.total_score = total_score
        self.correct_count = correct
        self.wrong_count = wrong
        self.unattempted_count = unattempted
        self.accuracy = accuracy.quantize(Decimal('0.01'))
        self.end_time = timezone.now()
        self.status = self.Status.AUTO_SUBMITTED if auto_submitted else self.Status.COMPLETED
        self.save()

        self._recalculate_ranks()

    def _recalculate_ranks(self):
        """Recomputes rank for every completed/auto-submitted attempt of this test, ordered by score desc."""
        completed_statuses = [self.Status.COMPLETED, self.Status.AUTO_SUBMITTED]
        attempts = list(
            TestAttempt.objects.filter(test=self.test, status__in=completed_statuses).order_by('-total_score', 'end_time')
        )
        for position, attempt in enumerate(attempts, start=1):
            if attempt.rank != position:
                TestAttempt.objects.filter(pk=attempt.pk).update(rank=position)

        # Invalidate the cached leaderboard (results/views.py) so the new submission's
        # score/rank shows up immediately instead of waiting for the cache TTL to expire.
        from django.core.cache import cache
        from results.services import leaderboard_cache_key
        cache.delete(leaderboard_cache_key(self.test_id))


class AnswerResponse(models.Model):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='responses')
    # PROTECT (not CASCADE): a question that a student has already answered must never
    # be hard-deleted — doing so would silently corrupt that student's historical score
    # (AnswerResponse rows disappearing without recalculating total_score/correct_count).
    # To retire a question, deactivate it (Question.is_active = False) instead of deleting.
    question = models.ForeignKey('questions.Question', on_delete=models.PROTECT)
    selected_option = models.CharField(max_length=1, null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    time_taken_seconds = models.PositiveIntegerField(null=True, blank=True)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ('attempt', 'question')

    def __str__(self):
        return f"{self.attempt} - Q{self.question_id}"
