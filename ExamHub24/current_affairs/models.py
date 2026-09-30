from django.db import models
from django.utils import timezone

from core.validators import validate_image_size
from questions.models import Question


class CurrentAffairQuerySet(models.QuerySet):
    def published(self):
        """
        Live-visible affairs: admin-approved (is_published) AND either not scheduled for
        the future, or that scheduled time has already passed. Filtering at query time
        (rather than a cron job flipping is_published) means scheduling works exactly on
        time without depending on a scheduled task actually running.
        """
        now = timezone.now()
        return self.filter(is_published=True).filter(
            models.Q(publish_at__isnull=True) | models.Q(publish_at__lte=now)
        )


class CurrentAffair(models.Model):
    class Category(models.TextChoices):
        NATIONAL = 'national', 'National'
        INTERNATIONAL = 'international', 'International'
        SPORTS = 'sports', 'Sports'
        ECONOMY = 'economy', 'Economy'
        SCIENCE = 'science', 'Science & Technology'
        AWARDS = 'awards', 'Awards & Honours'

    title = models.CharField(max_length=200)
    content = models.TextField()
    date = models.DateField()
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.NATIONAL)
    image = models.ImageField(upload_to='current_affairs/', null=True, blank=True, validators=[validate_image_size])
    source_link = models.URLField(blank=True)
    is_published = models.BooleanField(default=True, help_text='Admin approval to go live. Combined with "Publish at" below for scheduling.')
    publish_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Optional — set a future date/time to schedule this. Leave blank to publish immediately once "Is published" is checked.',
    )

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date', 'is_published'], name='idx_affair_date_published'),
        ]

    objects = CurrentAffairQuerySet.as_manager()

    def __str__(self):
        return self.title


class DailyQuiz(models.Model):
    date = models.DateField(unique=True)
    questions = models.ManyToManyField(Question, blank=True, related_name='daily_quizzes')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Daily Quiz - {self.date}"
