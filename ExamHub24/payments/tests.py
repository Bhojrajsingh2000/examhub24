"""
Integration test for the checkout flow with a coupon applied, using demo-mode payments
(no Razorpay keys configured in the test settings, so this exercises the same path a
local/PythonAnywhere setup without real gateway keys would use).

Run with:
    python manage.py test payments
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from subscriptions.models import Coupon, Plan, UserSubscription

from .models import Order

User = get_user_model()


class CheckoutWithCouponTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='buyer', password='pass12345', email='buyer@example.com')
        self.client.force_login(self.user)
        self.plan = Plan.objects.create(name='Gold Quarterly', price=Decimal('399.00'), duration_days=90, features='All tests')
        self.coupon = Coupon.objects.create(code='SAVE20', discount_type=Coupon.DiscountType.PERCENTAGE, discount_value=20)

    def test_checkout_without_coupon_charges_full_price(self):
        self.client.post(reverse('payments:create_order', args=[self.plan.id]))
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.amount, Decimal('399.00'))
        self.assertIsNone(order.coupon)

    def test_checkout_with_valid_coupon_applies_discount(self):
        self.client.post(reverse('payments:create_order', args=[self.plan.id]), {'coupon_code': 'save20'})
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.amount, Decimal('319.20'))
        self.assertEqual(order.coupon, self.coupon)
        self.assertEqual(order.original_amount, Decimal('399.00'))

        self.coupon.refresh_from_db()
        self.assertEqual(self.coupon.used_count, 1)

    def test_checkout_with_invalid_coupon_falls_back_to_full_price(self):
        response = self.client.post(
            reverse('payments:create_order', args=[self.plan.id]),
            {'coupon_code': 'DOESNOTEXIST'},
            follow=True,  # follow the redirect so the Django messages framework renders the warning
        )
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.amount, Decimal('399.00'))
        self.assertIsNone(order.coupon)
        self.assertContains(response, 'invalid or expired')

    def test_successful_demo_payment_activates_subscription_and_premium(self):
        self.client.post(reverse('payments:create_order', args=[self.plan.id]), {'coupon_code': 'SAVE20'})
        self.user.refresh_from_db()

        self.assertTrue(self.user.is_premium)
        self.assertTrue(UserSubscription.objects.filter(user=self.user, plan=self.plan, is_active=True).exists())


class AffiliateProgramTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer2', password='pass12345', email='buyer2@example.com')
        self.partner_user = User.objects.create_user(username='influencer', password='pass12345', email='influencer@example.com')
        self.plan = Plan.objects.create(name='Silver Monthly', price=Decimal('149.00'), duration_days=30, features='Free tests')

        from payments.models import AffiliatePartner
        self.partner = AffiliatePartner.objects.create(user=self.partner_user, code='INFLU10', commission_percent=Decimal('10'))

    def test_visiting_affiliate_link_stores_code_in_session_and_redirects(self):
        response = self.client.get(reverse('payments:affiliate_link', args=['influ10']))
        self.assertRedirects(response, reverse('subscriptions:plans'))
        self.assertEqual(self.client.session.get('affiliate_code'), 'INFLU10')

    def test_unknown_affiliate_code_does_not_error(self):
        response = self.client.get(reverse('payments:affiliate_link', args=['NOTREAL']))
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.client.session.get('affiliate_code'))

    def test_order_through_affiliate_link_credits_commission_on_demo_success(self):
        self.client.force_login(self.buyer)
        self.client.get(reverse('payments:affiliate_link', args=['INFLU10']))  # sets session
        self.client.post(reverse('payments:create_order', args=[self.plan.id]))

        order = Order.objects.get(user=self.buyer)
        self.assertEqual(order.affiliate, self.partner)

        self.partner.refresh_from_db()
        self.assertEqual(self.partner.total_referred_orders, 1)
        self.assertEqual(self.partner.total_earned, Decimal('14.90'))  # 10% of 149.00

    def test_order_without_affiliate_link_has_no_affiliate(self):
        self.client.force_login(self.buyer)
        self.client.post(reverse('payments:create_order', args=[self.plan.id]))
        order = Order.objects.get(user=self.buyer)
        self.assertIsNone(order.affiliate)

    def test_own_affiliate_dashboard_shows_own_stats_only(self):
        self.partner.total_earned = Decimal('50.00')
        self.partner.total_referred_orders = 3
        self.partner.save()

        self.client.force_login(self.partner_user)
        response = self.client.get(reverse('payments:affiliate_dashboard'))
        self.assertContains(response, 'INFLU10')
        self.assertEqual(response.context['partner'], self.partner)

    def test_non_affiliate_user_redirected_from_dashboard(self):
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('payments:affiliate_dashboard'))
        self.assertRedirects(response, reverse('dashboard:home'))


class RefundTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='refundee', password='pass12345', email='refundee@example.com')
        self.plan = Plan.objects.create(name='Gold Quarterly', price=Decimal('399.00'), duration_days=90, features='All tests')
        self.client.force_login(self.user)
        self.client.post(reverse('payments:create_order', args=[self.plan.id]))  # demo-mode instant success
        self.order = Order.objects.get(user=self.user)

    def test_refund_revokes_subscription_and_premium(self):
        from payments.services import process_refund

        self.assertTrue(self.user.is_premium)  # sanity check before refund
        result = process_refund(self.order, reason='Customer requested')

        self.assertTrue(result)
        self.order.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.REFUNDED)
        self.assertIsNotNone(self.order.refunded_at)
        self.assertFalse(self.user.is_premium)
        self.assertFalse(UserSubscription.objects.filter(user=self.user, plan=self.plan, is_active=True).exists())

    def test_refund_does_not_revoke_premium_if_another_active_subscription_exists(self):
        from payments.services import process_refund

        other_plan = Plan.objects.create(name='Silver Monthly', price=Decimal('149.00'), duration_days=30, features='Free tests')
        from datetime import timedelta
        from django.utils import timezone
        UserSubscription.objects.create(user=self.user, plan=other_plan, end_date=timezone.now().date() + timedelta(days=10), is_active=True)

        process_refund(self.order)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)  # still premium because of the other active subscription

    def test_double_refund_is_a_no_op(self):
        from payments.services import process_refund

        first = process_refund(self.order)
        second = process_refund(self.order)
        self.assertTrue(first)
        self.assertFalse(second)


class FreeTrialTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='trialist', password='pass12345', email='trialist@example.com')
        self.client.force_login(self.user)
        self.plan = Plan.objects.create(name='Gold Quarterly', price=Decimal('399.00'), duration_days=90, trial_days=7, features='All tests')

    def test_eligible_user_can_start_trial(self):
        response = self.client.post(reverse('subscriptions:start_trial', args=[self.plan.id]))
        self.assertRedirects(response, reverse('dashboard:home'))

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        sub = UserSubscription.objects.get(user=self.user, plan=self.plan)
        from datetime import timedelta
        from django.utils import timezone
        self.assertEqual(sub.end_date, timezone.now().date() + timedelta(days=7))

    def test_user_with_prior_subscription_is_not_trial_eligible(self):
        from datetime import timedelta
        from django.utils import timezone
        UserSubscription.objects.create(user=self.user, plan=self.plan, end_date=timezone.now().date() - timedelta(days=100), is_active=False)

        self.client.post(reverse('subscriptions:start_trial', args=[self.plan.id]))
        self.assertFalse(UserSubscription.objects.filter(user=self.user, end_date__gt=timezone.now().date()).exists())

    def test_plan_with_no_trial_days_is_never_eligible(self):
        no_trial_plan = Plan.objects.create(name='No Trial Plan', price=Decimal('99.00'), duration_days=30, trial_days=0)
        response = self.client.get(reverse('subscriptions:plan_detail', args=[no_trial_plan.id]))
        self.assertFalse(response.context['trial_eligible'])
