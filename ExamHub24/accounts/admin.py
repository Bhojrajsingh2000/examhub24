from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OTPVerification, StudentProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'full_name', 'email', 'phone_number', 'role', 'is_verified', 'is_premium', 'is_active')
    list_filter = ('role', 'is_verified', 'is_premium', 'is_active')
    search_fields = ('username', 'full_name', 'email', 'phone_number')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('ExamHub24 Profile', {
            'fields': ('phone_number', 'full_name', 'date_of_birth', 'gender', 'profile_picture',
                       'role', 'is_verified', 'is_premium', 'state', 'city'),
        }),
    )


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'target_exam', 'education_level', 'referral_code', 'referred_by', 'referral_reward_granted')
    search_fields = ('user__username', 'referral_code')
    list_filter = ('referral_reward_granted',)


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'purpose', 'is_used', 'created_at', 'expires_at')
    list_filter = ('purpose', 'is_used')
