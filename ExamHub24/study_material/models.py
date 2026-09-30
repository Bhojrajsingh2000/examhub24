from django.conf import settings
from django.db import models

from core.validators import validate_document_size, validate_image_size
from exams.models import Subject


class StudyMaterial(models.Model):
    class MaterialType(models.TextChoices):
        PDF = 'pdf', 'PDF Notes'
        NOTES = 'notes', 'Notes'
        PYQ = 'pyq', 'Previous Year Question Paper'

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='study_materials')
    title = models.CharField(max_length=150)
    file = models.FileField(upload_to='study_material/', validators=[validate_document_size])
    material_type = models.CharField(max_length=10, choices=MaterialType.choices, default=MaterialType.PDF)
    is_premium = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title


class VideoLecture(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='video_lectures')
    title = models.CharField(max_length=150)
    video_url = models.URLField()
    duration = models.PositiveIntegerField(help_text='Duration in minutes', default=0)
    thumbnail = models.ImageField(upload_to='video_thumbnails/', null=True, blank=True, validators=[validate_image_size])
    is_premium = models.BooleanField(default=False)

    def __str__(self):
        return self.title
