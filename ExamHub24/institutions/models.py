import random
import string

from django.conf import settings
from django.db import models


class Institution(models.Model):
    """
    A coaching center / school that gets its own signup code so its students' accounts
    are grouped together, and its designated staff can see aggregate performance across
    just their own students (see institutions/views.py institution_dashboard).
    """
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, unique=True, blank=True, help_text='Auto-generated if left blank — share this with students to join.')
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=15, blank=True)
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='administered_institutions',
        help_text='The user who can view this institution\'s dashboard.',
    )
    max_students = models.PositiveIntegerField(null=True, blank=True, help_text='License cap — leave blank for unlimited.')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)

    @property
    def student_count(self):
        return self.students.count()

    def has_capacity(self):
        return self.max_students is None or self.student_count < self.max_students
