"""
Finds likely duplicate questions — same subject, near-identical question text. Useful
after bulk CSV imports or when multiple instructors add content independently.

Usage:
    python manage.py find_duplicate_questions
"""
import difflib
from collections import defaultdict

from django.core.management.base import BaseCommand

from questions.models import Question

SIMILARITY_THRESHOLD = 0.85  # 0-1; higher = stricter (closer to exact match)


class Command(BaseCommand):
    help = 'Finds questions that are likely duplicates (same subject, very similar text).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold', type=float, default=SIMILARITY_THRESHOLD,
            help=f'Similarity threshold 0-1 (default {SIMILARITY_THRESHOLD}). Lower = more matches found.',
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        by_subject = defaultdict(list)
        for q in Question.objects.filter(is_active=True).only('id', 'subject_id', 'question_text'):
            by_subject[q.subject_id].append(q)

        total_pairs_found = 0
        for subject_id, questions in by_subject.items():
            for i in range(len(questions)):
                for j in range(i + 1, len(questions)):
                    q1, q2 = questions[i], questions[j]
                    ratio = difflib.SequenceMatcher(None, q1.question_text.lower(), q2.question_text.lower()).ratio()
                    if ratio >= threshold:
                        total_pairs_found += 1
                        self.stdout.write(self.style.WARNING(f'\nPossible duplicate ({ratio:.0%} similar), subject #{subject_id}:'))
                        self.stdout.write(f'  [{q1.id}] {q1.question_text[:80]}')
                        self.stdout.write(f'  [{q2.id}] {q2.question_text[:80]}')

        if total_pairs_found == 0:
            self.stdout.write(self.style.SUCCESS('No likely duplicates found.'))
        else:
            self.stdout.write(self.style.WARNING(
                f'\n{total_pairs_found} possible duplicate pair(s) found. Review manually in the admin panel — '
                f'this command only flags candidates, it does not delete anything automatically.'
            ))
