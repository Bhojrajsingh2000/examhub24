from django.conf import settings
from django.db import models
from django.utils import timezone

from exams.models import Exam
from questions.models import Question


class TestSeries(models.Model):
    class SeriesType(models.TextChoices):
        MOCK = 'mock', 'Mock Test Series'
        PREVIOUS_YEAR = 'previous_year', 'Previous Year Papers'
        SECTIONAL = 'sectional', 'Sectional / Topic-wise Practice'

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='test_series')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    series_type = models.CharField(max_length=20, choices=SeriesType.choices, default=SeriesType.MOCK)
    is_free = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    validity_days = models.PositiveIntegerField(default=365)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Test Series'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class MockTest(models.Model):
    series = models.ForeignKey(TestSeries, on_delete=models.CASCADE, related_name='mock_tests')
    title = models.CharField(max_length=150)
    duration_minutes = models.PositiveIntegerField(default=60)
    negative_marking = models.BooleanField(default=True)
    instructions = models.TextField(blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='self_generated_tests',
        help_text='Set for student-generated sectional practice tests; blank for admin-curated tests.',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def total_questions(self):
        # Uses .all() so Django's prefetch_related cache (set by the view) serves this
        # without a fresh query — calling .count() or .select_related() again here would
        # bypass that cache and cause an N+1 query problem when listing many tests.
        return len(self.test_questions.all())

    @property
    def total_marks(self):
        return sum(tq.effective_marks for tq in self.test_questions.all())

    def is_live(self):
        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return self.is_active

    def is_free_to_access(self, user):
        if self.series.is_free:
            return True
        return bool(user.is_authenticated and user.has_active_subscription())


class TestQuestion(models.Model):
    test = models.ForeignKey(MockTest, on_delete=models.CASCADE, related_name='test_questions')
    # PROTECT (not CASCADE): deleting a question that's already assigned to a test would
    # silently shrink that test's total_questions/total_marks — even for tests students
    # have already attempted and been scored against. Deactivate the question instead.
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    question_order = models.PositiveIntegerField(default=0)
    marks_override = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['question_order']
        unique_together = ('test', 'question')

    def __str__(self):
        return f"{self.test.title} - Q{self.question_order}"

    @property
    def effective_marks(self):
        return self.marks_override if self.marks_override is not None else self.question.marks
