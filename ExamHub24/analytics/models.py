from django.conf import settings
from django.db import models


class PerformanceAnalytics(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='performance_records')
    subject = models.ForeignKey('exams.Subject', on_delete=models.CASCADE, related_name='performance_records')
    attempts_count = models.PositiveIntegerField(default=0)
    avg_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    weak_topics = models.TextField(blank=True, help_text='Comma-separated tag names with low accuracy')
    strong_topics = models.TextField(blank=True, help_text='Comma-separated tag names with high accuracy')
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'subject')
        verbose_name_plural = 'Performance Analytics'

    def __str__(self):
        return f"{self.user} - {self.subject}"

    @classmethod
    def recalculate_for_user(cls, user):
        """
        Recomputes subject-wise performance analytics for a user based on all of their
        answered questions across completed test attempts. Called after each test submission
        (see results.models.TestAttempt.finalize / mock_tests.views.submit_test).
        """
        from results.models import AnswerResponse
        from exams.models import Subject

        responses = (
            AnswerResponse.objects
            .filter(attempt__user=user, attempt__status__in=['completed', 'auto_submitted'])
            .exclude(is_correct__isnull=True)
            .select_related('question', 'question__subject')
        )

        by_subject = {}
        for r in responses:
            by_subject.setdefault(r.question.subject_id, []).append(r)

        for subject_id, subject_responses in by_subject.items():
            subject = Subject.objects.filter(pk=subject_id).first()
            if not subject:
                continue
            total = len(subject_responses)
            correct = sum(1 for r in subject_responses if r.is_correct)
            avg_score = (correct / total * 100) if total else 0

            # Topic-level (tag-level) breakdown within this subject.
            tag_stats = {}
            for r in subject_responses:
                for tag in r.question.tags.all():
                    stats = tag_stats.setdefault(tag.name, {'correct': 0, 'total': 0})
                    stats['total'] += 1
                    if r.is_correct:
                        stats['correct'] += 1

            weak = [name for name, s in tag_stats.items() if s['total'] >= 3 and (s['correct'] / s['total']) < 0.5]
            strong = [name for name, s in tag_stats.items() if s['total'] >= 3 and (s['correct'] / s['total']) >= 0.75]

            cls.objects.update_or_create(
                user=user, subject=subject,
                defaults={
                    'attempts_count': total,
                    'avg_score': round(avg_score, 2),
                    'weak_topics': ', '.join(weak),
                    'strong_topics': ', '.join(strong),
                },
            )
