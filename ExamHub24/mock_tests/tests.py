"""
Tests for self-serve sectional test generation.

Run with:
    python manage.py test mock_tests
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from exams.models import Exam, ExamCategory, Subject
from questions.models import Question, QuestionTag

from .models import MockTest, TestQuestion, TestSeries
from .sectional import generate_sectional_test

User = get_user_model()


class SectionalTestGenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='frank', password='pass12345', email='frank@example.com')
        category = ExamCategory.objects.create(name='UPSC', slug='upsc')
        exam = Exam.objects.create(category=category, name='CSE Prelims', slug='cse-prelims')
        self.subject = Subject.objects.create(exam=exam, name='Polity')
        self.tag = QuestionTag.objects.create(name='Constitution')
        self.other_tag = QuestionTag.objects.create(name='Panchayati Raj')

        for i in range(5):
            q = Question.objects.create(
                subject=self.subject, question_text=f'Constitution Q{i}', option_a='A', option_b='B',
                option_c='C', option_d='D', correct_option='A',
            )
            q.tags.add(self.tag)

        for i in range(3):
            q = Question.objects.create(
                subject=self.subject, question_text=f'Panchayat Q{i}', option_a='A', option_b='B',
                option_c='C', option_d='D', correct_option='A',
            )
            q.tags.add(self.other_tag)

    def test_generates_test_with_requested_question_count(self):
        test = generate_sectional_test(self.user, self.subject, [self.tag], question_count=3, duration_minutes=10)
        self.assertIsNotNone(test)
        self.assertEqual(test.total_questions, 3)
        self.assertEqual(test.generated_by, self.user)
        self.assertEqual(test.duration_minutes, 10)

    def test_only_includes_questions_with_selected_tag(self):
        test = generate_sectional_test(self.user, self.subject, [self.tag], question_count=10, duration_minutes=10)
        # only 5 questions have this tag, even though 10 were requested and 8 exist total
        self.assertEqual(test.total_questions, 5)
        for tq in TestQuestion.objects.filter(test=test):
            self.assertIn(self.tag, tq.question.tags.all())

    def test_no_tags_draws_from_whole_subject(self):
        test = generate_sectional_test(self.user, self.subject, [], question_count=100, duration_minutes=10)
        self.assertEqual(test.total_questions, 8)  # all questions in the subject (5 + 3)

    def test_creates_dedicated_sectional_series(self):
        generate_sectional_test(self.user, self.subject, [self.tag], question_count=2, duration_minutes=10)
        self.assertTrue(TestSeries.objects.filter(series_type=TestSeries.SeriesType.SECTIONAL, exam=self.subject.exam).exists())

    def test_returns_none_when_no_matching_questions(self):
        empty_tag = QuestionTag.objects.create(name='Nonexistent Topic')
        test = generate_sectional_test(self.user, self.subject, [empty_tag], question_count=5, duration_minutes=10)
        self.assertIsNone(test)

    def test_builder_view_redirects_to_test_instructions(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('mock_tests:sectional_test_builder', args=[self.subject.id]), {
            'tags': [self.tag.id], 'question_count': 3, 'duration_minutes': 10,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/mock-tests/test/', response.url)


class TestSchedulingEnforcementTests(TestCase):
    """
    Confirms the fix for a real bug: MockTest.start_date/end_date were saved by admins
    but never actually checked before letting a student start a test — a test scheduled
    for later, or already closed, could be started at any time regardless.
    """

    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone

        self.user = User.objects.create_user(username='kate', password='pass12345', email='kate@example.com')
        self.client.force_login(self.user)
        category = ExamCategory.objects.create(name='Railways', slug='railways')
        exam = Exam.objects.create(category=category, name='RRB Group D', slug='rrb-group-d')
        series = TestSeries.objects.create(exam=exam, title='Live Tests', is_free=True)
        self.now = timezone.now()
        self.timedelta = timedelta
        self.series = series

    def test_cannot_start_a_test_scheduled_for_the_future(self):
        test = MockTest.objects.create(
            series=self.series, title='Future Test', duration_minutes=30,
            start_date=self.now + self.timedelta(days=1),
        )
        response = self.client.post(reverse('mock_tests:start_test', args=[test.id]))
        self.assertRedirects(response, reverse('mock_tests:test_instructions', args=[test.id]))

        from results.models import TestAttempt
        self.assertFalse(TestAttempt.objects.filter(user=self.user, test=test).exists())

    def test_cannot_start_a_test_whose_window_has_closed(self):
        test = MockTest.objects.create(
            series=self.series, title='Closed Test', duration_minutes=30,
            start_date=self.now - self.timedelta(days=2), end_date=self.now - self.timedelta(days=1),
        )
        self.client.post(reverse('mock_tests:start_test', args=[test.id]))

        from results.models import TestAttempt
        self.assertFalse(TestAttempt.objects.filter(user=self.user, test=test).exists())

    def test_can_start_a_test_currently_within_its_window(self):
        test = MockTest.objects.create(
            series=self.series, title='Live Test', duration_minutes=30,
            start_date=self.now - self.timedelta(hours=1), end_date=self.now + self.timedelta(hours=1),
        )
        self.client.post(reverse('mock_tests:start_test', args=[test.id]))

        from results.models import TestAttempt
        self.assertTrue(TestAttempt.objects.filter(user=self.user, test=test).exists())

    def test_can_resume_in_progress_attempt_even_after_window_closes(self):
        test = MockTest.objects.create(
            series=self.series, title='Just Closed Test', duration_minutes=30,
            start_date=self.now - self.timedelta(hours=2), end_date=self.now - self.timedelta(minutes=1),
        )
        from results.models import TestAttempt
        existing = TestAttempt.objects.create(user=self.user, test=test, status='in_progress')

        response = self.client.post(reverse('mock_tests:start_test', args=[test.id]))
        self.assertRedirects(response, reverse('mock_tests:attempt_test', args=[existing.id]))

    def test_test_with_no_schedule_dates_is_always_live(self):
        test = MockTest.objects.create(series=self.series, title='Always Open Test', duration_minutes=30)
        self.client.post(reverse('mock_tests:start_test', args=[test.id]))

        from results.models import TestAttempt
        self.assertTrue(TestAttempt.objects.filter(user=self.user, test=test).exists())


class SeriesListFilterSortTests(TestCase):
    def setUp(self):
        category = ExamCategory.objects.create(name='SSC', slug='ssc-sort-test')
        exam = Exam.objects.create(category=category, name='SSC CHSL', slug='ssc-chsl')
        self.cheap = TestSeries.objects.create(exam=exam, title='Cheap Series', price=99, series_type=TestSeries.SeriesType.MOCK)
        self.expensive = TestSeries.objects.create(exam=exam, title='Expensive Series', price=999, series_type=TestSeries.SeriesType.PREVIOUS_YEAR)

    def test_sort_by_price_ascending(self):
        response = self.client.get(reverse('mock_tests:series_list'), {'sort': 'price_asc'})
        titles = [s.title for s in response.context['all_series']]
        self.assertLess(titles.index('Cheap Series'), titles.index('Expensive Series'))

    def test_sort_by_price_descending(self):
        response = self.client.get(reverse('mock_tests:series_list'), {'sort': 'price_desc'})
        titles = [s.title for s in response.context['all_series']]
        self.assertLess(titles.index('Expensive Series'), titles.index('Cheap Series'))

    def test_filter_by_series_type(self):
        response = self.client.get(reverse('mock_tests:series_list'), {'type': 'previous_year'})
        titles = [s.title for s in response.context['all_series']]
        self.assertIn('Expensive Series', titles)
        self.assertNotIn('Cheap Series', titles)

    def test_invalid_type_param_is_ignored_not_erroring(self):
        response = self.client.get(reverse('mock_tests:series_list'), {'type': 'not-a-real-type'})
        self.assertEqual(response.status_code, 200)
