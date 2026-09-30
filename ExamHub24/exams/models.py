from django.conf import settings
from django.db import models
from django.urls import reverse

from core.validators import validate_document_size, validate_image_size


class ExamCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='category_icons/', null=True, blank=True, validators=[validate_image_size])
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Exam Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('exams:exam_list', args=[self.slug])


class Exam(models.Model):
    category = models.ForeignKey(ExamCategory, on_delete=models.CASCADE, related_name='exams')
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    exam_date = models.DateField(null=True, blank=True)
    syllabus_pdf = models.FileField(upload_to='syllabus/', null=True, blank=True, validators=[validate_document_size])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('exams:exam_detail', args=[self.slug])


class Subject(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.exam.name})"


class SyllabusTopic(models.Model):
    """A single checklist item within a subject's syllabus (e.g. 'Time & Work' under Quant)."""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='syllabus_topics')
    name = models.CharField(max_length=150)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.name} ({self.subject.name})"


class UserTopicProgress(models.Model):
    """Tracks whether a student has marked a given syllabus topic as studied/completed."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='topic_progress')
    topic = models.ForeignKey(SyllabusTopic, on_delete=models.CASCADE, related_name='progress_records')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'topic')

    def __str__(self):
        return f"{self.user} - {self.topic} - {'done' if self.is_completed else 'pending'}"
