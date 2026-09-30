"""
Auto-renewal for subscriptions flagged with auto_renew=True (see subscriptions.models.
UserSubscription.auto_renew — the field existed before but nothing ever acted on it).

IMPORTANT LIMITATION: this project's payment integration (payments/views.py) never
stores a reusable card/payment token — the demo-mode flow simulates instant success, and
the real Razorpay flow requires the student to complete checkout in their browser each
time. So this command can't silently charge a saved card like a real SaaS billing system
would. What it does instead: creates a new "pending" Order for each due renewal and
notifies the student to complete payment, so they don't lose access without warning.
Wiring up Razorpay's actual Subscriptions API (which DOES support auto-charging a
mandate) would be the real fix for production — documented as a next step in the README.

Usage:
    python manage.py process_auto_renewals

Recommended: run daily (same PythonAnywhere Scheduled Tasks pattern as
expire_subscriptions and cleanup_abandoned_attempts).
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from notifications.models import Notification
from payments.models import Order
from subscriptions.models import UserSubscription

RENEWAL_REMINDER_WINDOW_DAYS = 3  # notify this many days before expiry


class Command(BaseCommand):
    help = 'Notifies students whose auto-renew subscription is about to expire, and creates a pending renewal order.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        cutoff = today + timedelta(days=RENEWAL_REMINDER_WINDOW_DAYS)

        due_soon = UserSubscription.objects.filter(
            auto_renew=True, is_active=True, end_date__lte=cutoff, end_date__gte=today,
        ).select_related('user', 'plan')

        processed = 0
        for sub in due_soon:
            # Avoid spamming — skip if a pending/success renewal order was already created recently for this plan.
            already_handled = Order.objects.filter(
                user=sub.user, plan=sub.plan, created_at__date__gte=today - timedelta(days=RENEWAL_REMINDER_WINDOW_DAYS),
            ).exists()
            if already_handled:
                continue

            order = Order.objects.create(user=sub.user, plan=sub.plan, amount=sub.plan.price, status=Order.Status.PENDING)
            Notification.send(
                user=sub.user,
                title='Your subscription renews soon',
                message=(
                    f'Your {sub.plan.name} subscription expires on {sub.end_date:%d %b %Y}. '
                    f'Complete payment to renew and keep uninterrupted access.'
                ),
                notification_type=Notification.NotificationType.PAYMENT,
            )
            processed += 1
            self.stdout.write(f'Created pending renewal order #{order.id} for {sub.user} ({sub.plan.name}).')

        self.stdout.write(self.style.SUCCESS(f'Processed {processed} upcoming renewal(s).'))
