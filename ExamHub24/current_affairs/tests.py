"""
Tests for scheduled current-affairs publishing (query-time filtering via
CurrentAffair.objects.published() — no cron job needed for the scheduling itself).

Run with:
    python manage.py test current_affairs
"""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import CurrentAffair


class ScheduledPublishingTests(TestCase):
    def _make(self, title, is_published=True, publish_at=None):
        return CurrentAffair.objects.create(
            title=title, content='Some content', date=timezone.now().date(),
            category=CurrentAffair.Category.NATIONAL, is_published=is_published, publish_at=publish_at,
        )

    def test_unscheduled_published_article_is_visible(self):
        self._make('Immediate Article')
        response = self.client.get(reverse('current_affairs:list'))
        self.assertContains(response, 'Immediate Article')

    def test_future_scheduled_article_is_hidden(self):
        self._make('Future Article', publish_at=timezone.now() + timedelta(days=1))
        response = self.client.get(reverse('current_affairs:list'))
        self.assertNotContains(response, 'Future Article')

    def test_past_scheduled_article_is_visible(self):
        self._make('Already Due Article', publish_at=timezone.now() - timedelta(minutes=5))
        response = self.client.get(reverse('current_affairs:list'))
        self.assertContains(response, 'Already Due Article')

    def test_unpublished_article_is_hidden_regardless_of_schedule(self):
        self._make('Draft Article', is_published=False, publish_at=timezone.now() - timedelta(days=1))
        response = self.client.get(reverse('current_affairs:list'))
        self.assertNotContains(response, 'Draft Article')

    def test_future_article_detail_page_404s(self):
        article = self._make('Hidden Detail Article', publish_at=timezone.now() + timedelta(days=1))
        response = self.client.get(reverse('current_affairs:detail', args=[article.id]))
        self.assertEqual(response.status_code, 404)
