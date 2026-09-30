"""
Tests for core app views: health check, service worker/offline page (PWA), and the
homepage cache.

Run with:
    python manage.py test core
"""
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_check_returns_ok(self):
        response = self.client.get(reverse('core:health_check'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')


class PWATests(TestCase):
    def test_service_worker_served_at_root_with_correct_content_type(self):
        response = self.client.get('/service-worker.js')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/javascript')
        self.assertIn(b'CACHE_NAME', response.content)

    def test_offline_page_renders(self):
        response = self.client.get(reverse('core:offline'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You're offline")

    def test_manifest_json_is_served_as_static_file(self):
        # manifest.json lives in STATICFILES_DIRS, not a view — this just confirms the
        # file exists on disk where {% static %} expects it (full static-serving
        # behavior depends on runserver/collectstatic, not exercised by the test client).
        import os
        from django.conf import settings
        self.assertTrue(os.path.exists(os.path.join(settings.BASE_DIR, 'static', 'manifest.json')))


class HomepageCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_homepage_loads_and_populates_cache(self):
        from core.views import HOME_CACHE_KEY

        self.assertIsNone(cache.get(HOME_CACHE_KEY))
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(cache.get(HOME_CACHE_KEY))

    def test_clear_home_cache_helper_empties_it(self):
        from core.cache_utils import clear_home_cache
        from core.views import HOME_CACHE_KEY

        self.client.get(reverse('core:home'))
        self.assertIsNotNone(cache.get(HOME_CACHE_KEY))

        clear_home_cache()
        self.assertIsNone(cache.get(HOME_CACHE_KEY))


class SiteSearchTests(TestCase):
    def setUp(self):
        from exams.models import Exam, ExamCategory
        category = ExamCategory.objects.create(name='Banking', slug='banking')
        self.exam = Exam.objects.create(category=category, name='IBPS Clerk', slug='ibps-clerk', description='Bank clerk exam')

    def test_search_finds_matching_exam(self):
        response = self.client.get(reverse('core:search'), {'q': 'IBPS'})
        self.assertIn(self.exam, response.context['results']['exams'])

    def test_search_with_no_query_shows_no_results_section(self):
        response = self.client.get(reverse('core:search'))
        self.assertEqual(response.context['total_results'], 0)

    def test_search_with_no_matches_shows_empty_state(self):
        response = self.client.get(reverse('core:search'), {'q': 'zzzznomatch'})
        self.assertContains(response, 'No results found')
