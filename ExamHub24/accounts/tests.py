"""
Tests for the registration -> OTP verification -> login flow, including the OTP
lockout behavior added in a later update.

Run with:
    python manage.py test accounts
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .models import OTPVerification

User = get_user_model()


class RegistrationAndOTPTests(TestCase):
    def setUp(self):
        # Rate-limiting (core/throttle.py) uses the cache framework, which persists
        # across tests in the same run unlike the DB — clear it so one test's requests
        # don't trip the throttle for another.
        cache.clear()

    def _register(self):
        return self.client.post(reverse('accounts:register'), {
            'username': 'newstudent',
            'full_name': 'New Student',
            'email': 'newstudent@example.com',
            'phone_number': '9876543210',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })

    def test_registration_creates_unverified_user_and_otp(self):
        response = self._register()
        self.assertEqual(response.status_code, 302)  # redirected to OTP verify page

        user = User.objects.get(username='newstudent')
        self.assertFalse(user.is_verified)
        self.assertTrue(OTPVerification.objects.filter(user=user).exists())

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(username='existing', email='newstudent@example.com', password='x')
        response = self._register()
        self.assertEqual(response.status_code, 200)  # form re-rendered with error, no redirect
        self.assertContains(response, 'already exists')

    def test_correct_otp_verifies_and_logs_in(self):
        self._register()
        user = User.objects.get(username='newstudent')
        otp = OTPVerification.objects.filter(user=user).latest('created_at')

        response = self.client.post(reverse('accounts:verify_otp'), {'otp_code': otp.otp_code})
        self.assertEqual(response.status_code, 302)

        user.refresh_from_db()
        self.assertTrue(user.is_verified)
        # session should now be authenticated
        self.assertTrue(response.wsgi_request.user.is_authenticated or '_auth_user_id' in self.client.session)

    def test_wrong_otp_does_not_verify_and_increments_attempts(self):
        self._register()
        user = User.objects.get(username='newstudent')
        otp = OTPVerification.objects.filter(user=user).latest('created_at')

        self.client.post(reverse('accounts:verify_otp'), {'otp_code': '000000'})

        otp.refresh_from_db()
        user.refresh_from_db()
        self.assertFalse(user.is_verified)
        self.assertEqual(otp.attempts, 1)

    def test_otp_locks_out_after_max_attempts(self):
        self._register()
        user = User.objects.get(username='newstudent')
        otp = OTPVerification.objects.filter(user=user).latest('created_at')

        for _ in range(OTPVerification.MAX_ATTEMPTS):
            self.client.post(reverse('accounts:verify_otp'), {'otp_code': '000000'})

        otp.refresh_from_db()
        self.assertTrue(otp.is_used)  # locked out
        self.assertFalse(otp.is_valid())

        # Even the CORRECT code should no longer work once locked out.
        self.client.post(reverse('accounts:verify_otp'), {'otp_code': otp.otp_code})
        user.refresh_from_db()
        self.assertFalse(user.is_verified)

    def test_resend_otp_issues_a_new_working_code(self):
        self._register()
        user = User.objects.get(username='newstudent')
        old_otp = OTPVerification.objects.filter(user=user).latest('created_at')

        self.client.post(reverse('accounts:resend_otp'))
        new_otp = OTPVerification.objects.filter(user=user).latest('created_at')

        self.assertNotEqual(old_otp.pk, new_otp.pk)
        response = self.client.post(reverse('accounts:verify_otp'), {'otp_code': new_otp.otp_code})
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_verified)


class ReferralRewardTests(TestCase):
    def setUp(self):
        cache.clear()
        from subscriptions.models import Plan
        self.plan = Plan.objects.create(name='Silver Monthly', price=149, duration_days=30, features='Free tests')

        # referrer is an already-verified existing user
        self.referrer = User.objects.create_user(username='referrer', email='ref@example.com', password='pass12345', is_verified=True)
        StudentProfile.objects.get_or_create(user=self.referrer)

    def _register_with_code(self, code):
        return self.client.post(reverse('accounts:register'), {
            'username': 'referred_user',
            'full_name': 'Referred User',
            'email': 'referred@example.com',
            'phone_number': '9000000001',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'referral_code': code,
        })

    def test_valid_referral_code_links_profiles(self):
        code = self.referrer.student_profile.referral_code
        self._register_with_code(code)

        new_user = User.objects.get(username='referred_user')
        self.assertEqual(new_user.student_profile.referred_by, self.referrer)

    def test_reward_granted_on_otp_verification_for_both_users(self):
        code = self.referrer.student_profile.referral_code
        self._register_with_code(code)
        new_user = User.objects.get(username='referred_user')
        otp = OTPVerification.objects.filter(user=new_user).latest('created_at')

        self.client.post(reverse('accounts:verify_otp'), {'otp_code': otp.otp_code})

        new_user.refresh_from_db()
        self.referrer.refresh_from_db()
        self.assertTrue(new_user.is_premium)
        self.assertTrue(self.referrer.is_premium)
        new_user.student_profile.refresh_from_db()
        self.assertTrue(new_user.student_profile.referral_reward_granted)

    def test_invalid_referral_code_does_not_block_registration(self):
        response = self._register_with_code('NOTAREALCODE')
        self.assertEqual(response.status_code, 302)  # registration still succeeds
        new_user = User.objects.get(username='referred_user')
        self.assertIsNone(new_user.student_profile.referred_by)

    def test_reward_not_granted_twice(self):
        from subscriptions.services import grant_referral_reward
        code = self.referrer.student_profile.referral_code
        self._register_with_code(code)
        new_user = User.objects.get(username='referred_user')

        first = grant_referral_reward(new_user)
        second = grant_referral_reward(new_user)
        self.assertTrue(first)
        self.assertFalse(second)  # already granted — must not double-grant


class LoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='verifieduser', email='v@example.com', password='StrongPass123!', is_verified=True,
        )

    def test_login_with_correct_credentials(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'verifieduser', 'password': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'verifieduser', 'password': 'WrongPassword',
        })
        self.assertEqual(response.status_code, 200)  # re-renders form, no redirect
        self.assertFalse(response.wsgi_request.user.is_authenticated)
