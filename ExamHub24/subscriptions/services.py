"""
Referral reward logic. Kept separate from accounts/models.py to avoid a circular import
(accounts <-> subscriptions) and from subscriptions/models.py to keep that file focused
on schema.
"""
from datetime import timedelta

from django.utils import timezone

REFERRAL_BONUS_DAYS = 7


def grant_referral_reward(referred_user):
    """
    Called once, right after a referred user successfully verifies their OTP (see
    accounts/views.py verify_otp). Gives both the new user and whoever referred them
    REFERRAL_BONUS_DAYS of free access to the cheapest active plan. Idempotent — checks
    StudentProfile.referral_reward_granted so it can never fire twice for the same signup.
    """
    from .models import Plan, UserSubscription

    profile = getattr(referred_user, 'student_profile', None)
    if not profile or not profile.referred_by or profile.referral_reward_granted:
        return False

    plan = Plan.objects.filter(is_active=True).order_by('price').first()
    if not plan:
        return False  # no plan configured yet — nothing to grant, fail gracefully

    for user in (referred_user, profile.referred_by):
        _extend_free_access(user, plan, REFERRAL_BONUS_DAYS)

    profile.referral_reward_granted = True
    profile.save(update_fields=['referral_reward_granted'])
    return True


def _extend_free_access(user, plan, days):
    """Adds `days` of access on top of the user's current active subscription (if any), else starts fresh from today."""
    from .models import UserSubscription

    existing = UserSubscription.objects.filter(user=user, plan=plan, is_active=True).order_by('-end_date').first()
    start_base = existing.end_date if existing and existing.end_date >= timezone.now().date() else timezone.now().date()
    end_date = start_base + timedelta(days=days)

    UserSubscription.objects.create(user=user, plan=plan, end_date=end_date, is_active=True)
    user.is_premium = True
    user.save(update_fields=['is_premium'])
