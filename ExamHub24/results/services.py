"""
Shared post-submission logic used by both the live submit_test view (mock_tests/views.py)
and the cleanup_abandoned_attempts management command — kept in one place so the two
code paths can't drift out of sync.
"""


def leaderboard_cache_key(test_id):
    """
    Shared with results/models.py (TestAttempt._recalculate_ranks, which invalidates this
    key) and results/views.py (leaderboard, which reads/writes it) — defined once here so
    the two can't drift out of sync with different key formats.
    """
    return f'leaderboard_v1:{test_id}'


def finalize_and_notify(attempt, auto_submitted=False):
    """Finalizes scoring for an attempt, recalculates the user's analytics, and notifies them."""
    attempt.finalize(auto_submitted=auto_submitted)

    from analytics.models import PerformanceAnalytics
    PerformanceAnalytics.recalculate_for_user(attempt.user)

    from notifications.models import Notification
    Notification.send(
        user=attempt.user,
        title='Result Declared',
        message=f'Your result for "{attempt.test.title}" is ready — Score: {attempt.total_score}, Rank: #{attempt.rank}.',
        notification_type=Notification.NotificationType.RESULT,
    )
    return attempt
