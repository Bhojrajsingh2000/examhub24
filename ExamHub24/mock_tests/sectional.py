"""
Self-serve sectional/topic-wise test generation. Reuses the existing MockTest/TestAttempt
engine entirely (timer, auto-submit, scoring, leaderboard, results) — a sectional test is
just a MockTest with generated_by set and a small, topic-filtered question set, assigned
to a dedicated "Sectional Practice" TestSeries per exam (auto-created on first use).
"""
import random

from .models import MockTest, TestQuestion, TestSeries


def get_or_create_sectional_series(exam):
    series, _ = TestSeries.objects.get_or_create(
        exam=exam, series_type=TestSeries.SeriesType.SECTIONAL, title=f'{exam.name} — Sectional Practice',
        defaults={'description': 'Student-generated topic-wise practice tests.', 'is_free': True},
    )
    return series


def generate_sectional_test(user, subject, tags, question_count, duration_minutes):
    """
    Builds and returns a new MockTest with up to `question_count` random active questions
    from `subject`, optionally filtered to `tags` (a list of QuestionTag instances — pass
    an empty list/None to draw from the whole subject instead of specific topics).
    """
    from questions.models import Question

    pool = Question.objects.filter(subject=subject, is_active=True)
    if tags:
        pool = pool.filter(tags__in=tags).distinct()

    question_ids = list(pool.values_list('id', flat=True))
    random.shuffle(question_ids)
    selected_ids = question_ids[:question_count]

    if not selected_ids:
        return None  # not enough questions available for this subject/tag combination

    series = get_or_create_sectional_series(subject.exam)
    tag_label = ', '.join(t.name for t in tags) if tags else subject.name
    test = MockTest.objects.create(
        series=series,
        title=f'{tag_label} — Sectional Test ({len(selected_ids)}Q)',
        duration_minutes=duration_minutes,
        negative_marking=True,
        instructions='Self-generated sectional practice test based on your selected topics.',
        generated_by=user,
    )
    TestQuestion.objects.bulk_create([
        TestQuestion(test=test, question_id=qid, question_order=i)
        for i, qid in enumerate(selected_ids, start=1)
    ])
    return test
