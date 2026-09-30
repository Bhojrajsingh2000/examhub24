"""
Fixes a real gap in the original implementation: UserSubscription.end_date passing did
NOT automatically flip user.is_premium back to False, or is_active on the subscription
record. Run this daily (see note below) to keep premium access in sync with actual
subscription validity.

Usage:
    python manage.py expire_subscriptions

Recommended: schedule this to run once daily. On PythonAnywhere, use the free
"Scheduled Tasks" feature (Web tab isn't needed for this — it's under the "Tasks" tab)
and point it at:
    python /home/yourusername/ExamHub24/manage.py expire_subscriptions
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from subscriptions.models import UserSubscription


class Command(BaseCommand):
    help = 'Deactivates expired subscriptions and downgrades users who have no remaining active subscription.'

    def handle(self, *args, **options):
        today = timezone.now().date()

        expired = UserSubscription.objects.filter(is_active=True, end_date__lt=today)
        expired_count = expired.count()
        expired.update(is_active=False)

        # A user should only lose premium status if they have NO other still-active,
        # still-valid subscription (e.g. an overlapping renewal).
        downgraded = 0
        affected_user_ids = set(
            UserSubscription.objects.filter(is_active=False, end_date__lt=today).values_list('user_id', flat=True)
        )
        for user_id in affected_user_ids:
            still_valid = UserSubscription.objects.filter(
                user_id=user_id, is_active=True, end_date__gte=today
            ).exists()
            if not still_valid:
                from accounts.models import User
                updated = User.objects.filter(pk=user_id, is_premium=True).update(is_premium=False)
                downgraded += updated

        self.stdout.write(self.style.SUCCESS(
            f'Expired {expired_count} subscription record(s); downgraded {downgraded} user(s) from premium.'
        ))
