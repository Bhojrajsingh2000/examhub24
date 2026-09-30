"""
Tests for question bookmarking and Practice Mode (instant-feedback, no-timer practice).

Run with:
    python manage.py test questions
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from exams.models import Exam, ExamCategory, Subject

from .models import BookmarkedQuestion, Question

User = get_user_model()


class BookmarkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dave', password='pass12345', email='dave@example.com')
        self.client.force_login(self.user)
        category = ExamCategory.objects.create(name='SSC', slug='ssc')
        exam = Exam.objects.create(category=category, name='SSC CGL', slug='ssc-cgl')
        subject = Subject.objects.create(exam=exam, name='English')
        self.question = Question.objects.create(
            subject=subject, question_text='Synonym of Happy?', option_a='Sad', option_b='Joyful',
            option_c='Angry', option_d='Tired', correct_option='B',
        )

    def test_toggle_bookmark_on_then_off(self):
        url = reverse('questions:bookmark_toggle', args=[self.question.id])

        response = self.client.post(url)
        self.assertEqual(response.json()['bookmarked'], True)
        self.assertTrue(BookmarkedQuestion.objects.filter(user=self.user, question=self.question).exists())

        response = self.client.post(url)
        self.assertEqual(response.json()['bookmarked'], False)
        self.assertFalse(BookmarkedQuestion.objects.filter(user=self.user, question=self.question).exists())

    def test_bookmark_list_shows_bookmarked_question(self):
        BookmarkedQuestion.objects.create(user=self.user, question=self.question)
        response = self.client.get(reverse('questions:bookmark_list'))
        self.assertContains(response, 'Synonym of Happy?')

    def test_bookmarking_requires_login(self):
        self.client.logout()
        url = reverse('questions:bookmark_toggle', args=[self.question.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)  # redirected to login


class PracticeModeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='erin', password='pass12345', email='erin@example.com')
        self.client.force_login(self.user)
        category = ExamCategory.objects.create(name='Railways', slug='railways')
        exam = Exam.objects.create(category=category, name='RRB NTPC', slug='rrb-ntpc')
        self.subject = Subject.objects.create(exam=exam, name='General Science')
        self.question = Question.objects.create(
            subject=self.subject, question_text='H2O is commonly known as?', option_a='Salt',
            option_b='Water', option_c='Sugar', option_d='Acid', correct_option='B',
            explanation='H2O is the chemical formula for water.',
        )

    def test_practice_session_shows_a_question(self):
        response = self.client.get(reverse('questions:practice_session', args=[self.subject.id]))
        self.assertContains(response, 'H2O is commonly known as?')
        self.assertIsNone(response.context['feedback'])  # no answer submitted yet

    def test_correct_answer_gives_correct_feedback(self):
        response = self.client.post(reverse('questions:practice_session', args=[self.subject.id]), {
            'question_id': self.question.id, 'selected_option': 'B',
        })
        self.assertTrue(response.context['feedback']['is_correct'])

    def test_wrong_answer_gives_incorrect_feedback_and_explanation(self):
        response = self.client.post(reverse('questions:practice_session', args=[self.subject.id]), {
            'question_id': self.question.id, 'selected_option': 'A',
        })
        self.assertFalse(response.context['feedback']['is_correct'])
        self.assertContains(response, 'chemical formula for water')

    def test_practice_does_not_create_a_test_attempt(self):
        from results.models import TestAttempt
        self.client.post(reverse('questions:practice_session', args=[self.subject.id]), {
            'question_id': self.question.id, 'selected_option': 'B',
        })
        # Practice Mode must never touch scoring/leaderboards — no TestAttempt should exist.
        self.assertEqual(TestAttempt.objects.count(), 0)

    def test_empty_subject_shows_no_questions_message(self):
        empty_subject = Subject.objects.create(exam=self.subject.exam, name='Empty Subject')
        response = self.client.get(reverse('questions:practice_session', args=[empty_subject.id]))
        self.assertContains(response, 'No questions available')
