"""
Tests for the syllabus checklist tracker (SyllabusTopic / UserTopicProgress).

Run with:
    python manage.py test exams
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Exam, ExamCategory, Subject, SyllabusTopic, UserTopicProgress

User = get_user_model()


class SyllabusChecklistTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='grace', password='pass12345', email='grace@example.com')
        self.client.force_login(self.user)
        category = ExamCategory.objects.create(name='SSC', slug='ssc')
        self.exam = Exam.objects.create(category=category, name='SSC CGL', slug='ssc-cgl')
        self.subject = Subject.objects.create(exam=self.exam, name='Reasoning')
        self.topic1 = SyllabusTopic.objects.create(subject=self.subject, name='Coding-Decoding', order=1)
        self.topic2 = SyllabusTopic.objects.create(subject=self.subject, name='Blood Relations', order=2)

    def test_checklist_shows_zero_percent_initially(self):
        response = self.client.get(reverse('exams:syllabus_checklist', args=[self.exam.slug]))
        self.assertEqual(response.context['overall_pct'], 0)
        self.assertEqual(response.context['total_topics'], 2)

    def test_toggle_marks_topic_completed(self):
        url = reverse('exams:toggle_topic_progress', args=[self.topic1.id])
        response = self.client.post(url)
        self.assertTrue(response.json()['is_completed'])
        self.assertTrue(UserTopicProgress.objects.get(user=self.user, topic=self.topic1).is_completed)

    def test_toggle_twice_marks_incomplete_again(self):
        url = reverse('exams:toggle_topic_progress', args=[self.topic1.id])
        self.client.post(url)
        response = self.client.post(url)
        self.assertFalse(response.json()['is_completed'])

    def test_overall_progress_reflects_completed_topics(self):
        UserTopicProgress.objects.create(user=self.user, topic=self.topic1, is_completed=True)
        response = self.client.get(reverse('exams:syllabus_checklist', args=[self.exam.slug]))
        self.assertEqual(response.context['overall_pct'], 50)  # 1 of 2 topics done

    def test_progress_is_per_user(self):
        other_user = User.objects.create_user(username='henry', password='pass12345', email='henry@example.com')
        UserTopicProgress.objects.create(user=other_user, topic=self.topic1, is_completed=True)

        response = self.client.get(reverse('exams:syllabus_checklist', args=[self.exam.slug]))
        self.assertEqual(response.context['overall_pct'], 0)  # grace's own progress is still 0
