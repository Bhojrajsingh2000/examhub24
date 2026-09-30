"""
Students sometimes start a test and close the browser tab without submitting — leaving
behind an 'in_progress' TestAttempt forever (it never expires or gets scored, and blocks
'resume' logic from ever showing a clean slate). This command finds attempts that have
clearly run past their allotted time and auto-submits them, same as if the timer had
expired in-browser.

Usage:
    python manage.py cleanup_abandoned_attempts

Recommended: schedule this to run every hour or so (PythonAnywhere Scheduled Tasks).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from results.models import TestAttempt


class Command(BaseCommand):
    help = "Auto-submits 'in_progress' test attempts whose time limit has clearly passed (abandoned browser tabs)."

    def handle(self, *args, **options):
        now = timezone.now()
        stale_attempts = TestAttempt.objects.filter(status=TestAttempt.Status.IN_PROGRESS).select_related('test')

        finalized = 0
        for attempt in stale_attempts:
            deadline = attempt.start_time + timezone.timedelta(minutes=attempt.test.duration_minutes)
            # Small grace period (5 minutes) in case of clock skew / last-second submits.
            if now > deadline + timezone.timedelta(minutes=5):
                from results.services import finalize_and_notify
                finalize_and_notify(attempt, auto_submitted=True)
                finalized += 1

        self.stdout.write(self.style.SUCCESS(f'Auto-submitted {finalized} abandoned test attempt(s).'))
