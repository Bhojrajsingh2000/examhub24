"""
Tests for institution code signup linking and the institution dashboard.

Run with:
    python manage.py test institutions
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from accounts.models import OTPVerification, StudentProfile

from .models import Institution

User = get_user_model()


class InstitutionSignupTests(TestCase):
    def setUp(self):
        cache.clear()
        self.institution = Institution.objects.create(name='Bright Academy', code='BRIGHT01')

    def _register(self, institution_code=''):
        return self.client.post(reverse('accounts:register'), {
            'username': 'institute_student',
            'full_name': 'Institute Student',
            'email': 'institute_student@example.com',
            'phone_number': '9111111111',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'institution_code': institution_code,
        })

    def test_valid_institution_code_links_student(self):
        self._register('bright01')  # lowercase — should still match (normalized to upper)
        user = User.objects.get(username='institute_student')
        self.assertEqual(user.student_profile.institution, self.institution)

    def test_invalid_institution_code_does_not_block_registration(self):
        response = self._register('NOPE123')
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='institute_student')
        self.assertIsNone(user.student_profile.institution)

    def test_full_institution_rejects_new_signups(self):
        self.institution.max_students = 0
        self.institution.save()
        self._register('BRIGHT01')
        user = User.objects.get(username='institute_student')
        self.assertIsNone(user.student_profile.institution)


class InstitutionDashboardAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='inst_owner', password='pass12345', email='owner@example.com')
        self.other_user = User.objects.create_user(username='rando', password='pass12345', email='rando@example.com')
        self.institution = Institution.objects.create(name='Test Institute', admin_user=self.owner)

    def test_owner_can_access_dashboard(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('institutions:institution_dashboard', args=[self.institution.id]))
        self.assertEqual(response.status_code, 200)

    def test_other_user_cannot_access_dashboard(self):
        self.client.force_login(self.other_user)
        response = self.client.get(reverse('institutions:institution_dashboard', args=[self.institution.id]))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_access_any_institution_dashboard(self):
        staff_user = User.objects.create_user(username='staffer', password='pass12345', email='staff@example.com', is_staff=True)
        self.client.force_login(staff_user)
        response = self.client.get(reverse('institutions:institution_dashboard', args=[self.institution.id]))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_counts_only_this_institutions_students(self):
        student = User.objects.create_user(username='linked_student', password='pass12345', email='linked@example.com')
        StudentProfile.objects.create(user=student, institution=self.institution)

        unrelated_student = User.objects.create_user(username='other_student', password='pass12345', email='other@example.com')
        StudentProfile.objects.create(user=unrelated_student)  # no institution

        self.client.force_login(self.owner)
        response = self.client.get(reverse('institutions:institution_dashboard', args=[self.institution.id]))
        self.assertEqual(response.context['total_students'], 1)
