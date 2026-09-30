from django.conf import settings
from django.db import models

from core.validators import validate_image_size
from exams.models import Subject


class QuestionTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Question(models.Model):
    class Difficulty(models.TextChoices):
        EASY = 'easy', 'Easy'
        MEDIUM = 'medium', 'Medium'
        HARD = 'hard', 'Hard'

    class Option(models.TextChoices):
        A = 'A', 'A'
        B = 'B', 'B'
        C = 'C', 'C'
        D = 'D', 'D'

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_image = models.ImageField(upload_to='questions/', null=True, blank=True, validators=[validate_image_size])

    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=1, choices=Option.choices)

    explanation = models.TextField(blank=True)
    video_solution_url = models.URLField(blank=True, help_text='Optional YouTube/Vimeo link explaining the solution.')
    difficulty_level = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    negative_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0.25)

    tags = models.ManyToManyField(QuestionTag, blank=True, related_name='questions')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subject', 'is_active'], name='idx_question_subject_active'),
        ]

    def __str__(self):
        return self.question_text[:60]

    def get_option_text(self, option_letter):
        return getattr(self, f'option_{option_letter.lower()}', '')

    @property
    def correct_answer_text(self):
        """Convenience for templates, where calling get_option_text(dynamic_arg) isn't possible."""
        return self.get_option_text(self.correct_option)

    def check_answer(self, selected_option):
        return selected_option == self.correct_option


class BookmarkedQuestion(models.Model):
    """Lets a student save a question (e.g. from a result's solution page) to revisit later."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookmarked_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='bookmarked_by')
    note = models.CharField(max_length=255, blank=True, help_text="Optional personal note, e.g. 'revise this formula'.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'question')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} bookmarked Q{self.question_id}"
