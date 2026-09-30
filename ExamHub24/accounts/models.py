import random
import string
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from core.validators import validate_image_size


class User(AbstractUser):
    """Custom user model — extends Django's AbstractUser with exam-prep specific fields."""

    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        ADMIN = 'admin', 'Admin'
        INSTRUCTOR = 'instructor', 'Instructor'

    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'
        OTHER = 'O', 'Other'

    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=150, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True, validators=[validate_image_size])
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    is_verified = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    state = models.CharField(max_length=50, blank=True)
    city = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.username

    def has_active_subscription(self):
        """Checks subscriptions app for a currently-valid subscription."""
        from subscriptions.models import UserSubscription
        return UserSubscription.objects.filter(
            user=self, is_active=True, end_date__gte=timezone.now().date()
        ).exists()


class StudentProfile(models.Model):
    """Additional exam-prep specific profile info for a student."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    target_exam = models.ForeignKey('exams.Exam', on_delete=models.SET_NULL, null=True, blank=True)
    education_level = models.CharField(max_length=50, blank=True)
    college_name = models.CharField(max_length=150, blank=True)
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals_made',
        help_text='The user whose referral code this student signed up with.',
    )
    referral_reward_granted = models.BooleanField(default=False)
    institution = models.ForeignKey(
        'institutions.Institution', on_delete=models.SET_NULL, null=True, blank=True, related_name='students',
        help_text='Set automatically if the student signed up with an institution code.',
    )

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Profile: {self.user}"


class OTPVerification(models.Model):
    """One-time-password records used for registration / password reset."""

    class Purpose(models.TextChoices):
        REGISTRATION = 'registration', 'Registration'
        PASSWORD_RESET = 'password_reset', 'Password Reset'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='otps')
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices, default=Purpose.REGISTRATION)
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    MAX_ATTEMPTS = 5

    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = ''.join(random.choices(string.digits, k=6))
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        return (not self.is_used) and self.attempts < self.MAX_ATTEMPTS and timezone.now() <= self.expires_at

    def register_failed_attempt(self):
        self.attempts += 1
        if self.attempts >= self.MAX_ATTEMPTS:
            self.is_used = True  # lock this OTP out; user must request a fresh one
        self.save(update_fields=['attempts', 'is_used'])

    def __str__(self):
        return f"OTP for {self.user} ({self.purpose})"
