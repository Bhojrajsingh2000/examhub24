"""
Tests for TestAttempt.finalize() — the scoring engine. These are the most important
tests in the project: if this logic breaks, every student's score/rank is wrong.

Run with:
    python manage.py test results
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from exams.models import Exam, ExamCategory, Subject
from mock_tests.models import MockTest, TestQuestion, TestSeries
from questions.models import Question

from .models import AnswerResponse, TestAttempt

User = get_user_model()


class ScoreCalculationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345', email='alice@example.com')

        category = ExamCategory.objects.create(name='Banking', slug='banking')
        exam = Exam.objects.create(category=category, name='IBPS PO', slug='ibps-po')
        subject = Subject.objects.create(exam=exam, name='Quant')
        series = TestSeries.objects.create(exam=exam, title='Free Series', is_free=True)
        self.test = MockTest.objects.create(series=series, title='Mock 1', duration_minutes=30, negative_marking=True)

        # 4 questions: 1 mark each, 0.25 negative marking each.
        self.questions = []
        for i in range(4):
            q = Question.objects.create(
                subject=subject, question_text=f'Q{i}', option_a='A', option_b='B',
                option_c='C', option_d='D', correct_option='A', marks=1, negative_marks=Decimal('0.25'),
            )
            TestQuestion.objects.create(test=self.test, question=q, question_order=i)
            self.questions.append(q)

    def _make_attempt(self):
        return TestAttempt.objects.create(user=self.user, test=self.test, status=TestAttempt.Status.IN_PROGRESS)

    def test_all_correct_gives_full_marks(self):
        attempt = self._make_attempt()
        for q in self.questions:
            AnswerResponse.objects.create(attempt=attempt, question=q, selected_option='A')  # 'A' is always correct here

        attempt.finalize()

        self.assertEqual(attempt.correct_count, 4)
        self.assertEqual(attempt.wrong_count, 0)
        self.assertEqual(attempt.unattempted_count, 0)
        self.assertEqual(attempt.total_score, Decimal('4.00'))
        self.assertEqual(attempt.accuracy, Decimal('100.00'))
        self.assertEqual(attempt.status, TestAttempt.Status.COMPLETED)

    def test_negative_marking_applied_on_wrong_answers(self):
        attempt = self._make_attempt()
        AnswerResponse.objects.create(attempt=attempt, question=self.questions[0], selected_option='A')  # correct
        AnswerResponse.objects.create(attempt=attempt, question=self.questions[1], selected_option='B')  # wrong
        AnswerResponse.objects.create(attempt=attempt, question=self.questions[2], selected_option='C')  # wrong
        AnswerResponse.objects.create(attempt=attempt, question=self.questions[3], selected_option=None)  # unattempted

        attempt.finalize()

        # +1 (correct) - 0.25 - 0.25 (two wrong) + 0 (unattempted) = 0.50
        self.assertEqual(attempt.correct_count, 1)
        self.assertEqual(attempt.wrong_count, 2)
        self.assertEqual(attempt.unattempted_count, 1)
        self.assertEqual(attempt.total_score, Decimal('0.50'))
        # accuracy is correct/attempted, not correct/total: 1 correct out of 3 attempted
        self.assertEqual(attempt.accuracy, Decimal('33.33'))

    def test_no_negative_marking_when_disabled(self):
        self.test.negative_marking = False
        self.test.save()
        attempt = self._make_attempt()
        AnswerResponse.objects.create(attempt=attempt, question=self.questions[0], selected_option='B')  # wrong

        attempt.finalize()

        self.assertEqual(attempt.wrong_count, 1)
        self.assertEqual(attempt.total_score, Decimal('0.00'))  # no penalty

    def test_all_unattempted_gives_zero_score_no_crash(self):
        attempt = self._make_attempt()
        for q in self.questions:
            AnswerResponse.objects.create(attempt=attempt, question=q, selected_option=None)

        attempt.finalize()

        self.assertEqual(attempt.total_score, Decimal('0.00'))
        self.assertEqual(attempt.unattempted_count, 4)
        self.assertEqual(attempt.accuracy, Decimal('0.00'))  # must not divide by zero

    def test_rank_is_calculated_across_multiple_attempts(self):
        user2 = User.objects.create_user(username='bob', password='pass12345', email='bob@example.com')

        attempt1 = self._make_attempt()
        for q in self.questions:
            AnswerResponse.objects.create(attempt=attempt1, question=q, selected_option='A')  # all correct -> 4.0
        attempt1.finalize()

        attempt2 = TestAttempt.objects.create(user=user2, test=self.test, status=TestAttempt.Status.IN_PROGRESS)
        AnswerResponse.objects.create(attempt=attempt2, question=self.questions[0], selected_option='A')  # 1 correct -> 1.0
        for q in self.questions[1:]:
            AnswerResponse.objects.create(attempt=attempt2, question=q, selected_option=None)
        attempt2.finalize()

        attempt1.refresh_from_db()
        attempt2.refresh_from_db()
        self.assertEqual(attempt1.rank, 1)  # higher score
        self.assertEqual(attempt2.rank, 2)

    def test_auto_submitted_flag_sets_correct_status(self):
        attempt = self._make_attempt()
        attempt.finalize(auto_submitted=True)
        self.assertEqual(attempt.status, TestAttempt.Status.AUTO_SUBMITTED)


class DataIntegrityTests(TestCase):
    """
    Confirms the on_delete=PROTECT fix: a question that's already been answered by a
    student must not be hard-deletable, since that would silently corrupt their
    historical score. Deactivating (is_active=False) is the safe alternative.
    """

    def setUp(self):
        self.user = User.objects.create_user(username='carol', password='pass12345', email='carol@example.com')
        category = ExamCategory.objects.create(name='SSC', slug='ssc')
        exam = Exam.objects.create(category=category, name='SSC CGL', slug='ssc-cgl')
        subject = Subject.objects.create(exam=exam, name='Reasoning')
        series = TestSeries.objects.create(exam=exam, title='Free Series', is_free=True)
        self.test = MockTest.objects.create(series=series, title='Mock 1', duration_minutes=30)
        self.question = Question.objects.create(
            subject=subject, question_text='Q1', option_a='A', option_b='B',
            option_c='C', option_d='D', correct_option='A',
        )
        TestQuestion.objects.create(test=self.test, question=self.question, question_order=1)

    def test_question_with_no_attempts_can_still_be_deleted(self):
        # No AnswerResponse exists yet -> only the TestQuestion link protects it via PROTECT,
        # so removing the TestQuestion first should allow deletion.
        TestQuestion.objects.filter(question=self.question).delete()
        self.question.delete()  # should not raise
        self.assertFalse(Question.objects.filter(pk=self.question.pk).exists())

    def test_question_answered_by_a_student_cannot_be_deleted(self):
        from django.db.models import ProtectedError

        attempt = TestAttempt.objects.create(user=self.user, test=self.test, status=TestAttempt.Status.IN_PROGRESS)
        AnswerResponse.objects.create(attempt=attempt, question=self.question, selected_option='A')

        with self.assertRaises(ProtectedError):
            self.question.delete()

        # The safe alternative still works and doesn't touch the historical record.
        self.question.is_active = False
        self.question.save()
        self.assertTrue(Question.objects.filter(pk=self.question.pk, is_active=False).exists())
        self.assertTrue(AnswerResponse.objects.filter(attempt=attempt, question=self.question).exists())
