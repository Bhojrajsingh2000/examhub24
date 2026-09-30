"""
Tests for Coupon discount calculation and validity checks.

Run with:
    python manage.py test subscriptions
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .models import Coupon, Plan, UserSubscription


class CouponTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(name='Gold Quarterly', price=Decimal('399.00'), duration_days=90, features='All tests')

    def test_percentage_discount(self):
        coupon = Coupon.objects.create(code='save20', discount_type=Coupon.DiscountType.PERCENTAGE, discount_value=20)
        self.assertEqual(coupon.code, 'SAVE20')  # normalized to uppercase on save
        discounted = coupon.calculate_discounted_price(self.plan.price)
        self.assertEqual(discounted, Decimal('319.20'))

    def test_flat_discount(self):
        coupon = Coupon.objects.create(code='FLAT50', discount_type=Coupon.DiscountType.FLAT, discount_value=50)
        discounted = coupon.calculate_discounted_price(self.plan.price)
        self.assertEqual(discounted, Decimal('349.00'))

    def test_discount_never_goes_below_zero(self):
        coupon = Coupon.objects.create(code='HUGE', discount_type=Coupon.DiscountType.FLAT, discount_value=1000)
        discounted = coupon.calculate_discounted_price(self.plan.price)
        self.assertEqual(discounted, Decimal('0'))

    def test_expired_coupon_is_invalid(self):
        coupon = Coupon.objects.create(
            code='OLD10', discount_type=Coupon.DiscountType.PERCENTAGE, discount_value=10,
            valid_until=timezone.now() - timezone.timedelta(days=1),
        )
        self.assertFalse(coupon.is_valid_for_plan(self.plan))

    def test_max_uses_exhausted_is_invalid(self):
        coupon = Coupon.objects.create(
            code='LIMITED', discount_type=Coupon.DiscountType.FLAT, discount_value=10,
            max_uses=1, used_count=1,
        )
        self.assertFalse(coupon.is_valid_for_plan(self.plan))

    def test_inactive_coupon_is_invalid(self):
        coupon = Coupon.objects.create(code='OFF', discount_type=Coupon.DiscountType.FLAT, discount_value=10, is_active=False)
        self.assertFalse(coupon.is_valid_for_plan(self.plan))

    def test_coupon_restricted_to_other_plan_is_invalid(self):
        other_plan = Plan.objects.create(name='Silver Monthly', price=Decimal('149.00'), duration_days=30, features='Free tests')
        coupon = Coupon.objects.create(code='SILVERONLY', discount_type=Coupon.DiscountType.FLAT, discount_value=10)
        coupon.applicable_plans.add(other_plan)
        self.assertFalse(coupon.is_valid_for_plan(self.plan))
        self.assertTrue(coupon.is_valid_for_plan(other_plan))

    def test_valid_coupon_with_no_restrictions(self):
        coupon = Coupon.objects.create(code='OPEN', discount_type=Coupon.DiscountType.FLAT, discount_value=10)
        self.assertTrue(coupon.is_valid_for_plan(self.plan))


class AutoRenewalCommandTests(TestCase):
    """
    Tests for the process_auto_renewals management command.
    Run with: python manage.py test subscriptions
    """

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username='renewme', password='pass12345', email='renewme@example.com')
        self.renewal_plan = Plan.objects.create(name='Gold Quarterly Renewal', price=Decimal('399.00'), duration_days=90, features='All tests')

    def test_creates_pending_order_and_notification_for_subscription_expiring_soon(self):
        from datetime import timedelta

        from django.core.management import call_command
        from django.utils import timezone

        from notifications.models import Notification
        from payments.models import Order

        UserSubscription.objects.create(
            user=self.user, plan=self.renewal_plan, end_date=timezone.now().date() + timedelta(days=2),
            is_active=True, auto_renew=True,
        )
        call_command('process_auto_renewals')

        self.assertTrue(Order.objects.filter(user=self.user, plan=self.renewal_plan, status=Order.Status.PENDING).exists())
        self.assertTrue(Notification.objects.filter(user=self.user, notification_type=Notification.NotificationType.PAYMENT).exists())

    def test_does_not_process_subscription_without_auto_renew(self):
        from datetime import timedelta

        from django.core.management import call_command
        from django.utils import timezone

        from payments.models import Order

        UserSubscription.objects.create(
            user=self.user, plan=self.renewal_plan, end_date=timezone.now().date() + timedelta(days=2),
            is_active=True, auto_renew=False,
        )
        call_command('process_auto_renewals')
        self.assertFalse(Order.objects.filter(user=self.user, plan=self.renewal_plan).exists())

    def test_does_not_duplicate_order_if_already_handled_recently(self):
        from datetime import timedelta

        from django.core.management import call_command
        from django.utils import timezone

        from payments.models import Order

        UserSubscription.objects.create(
            user=self.user, plan=self.renewal_plan, end_date=timezone.now().date() + timedelta(days=1),
            is_active=True, auto_renew=True,
        )
        call_command('process_auto_renewals')
        call_command('process_auto_renewals')  # run again immediately
        self.assertEqual(Order.objects.filter(user=self.user, plan=self.renewal_plan).count(), 1)
