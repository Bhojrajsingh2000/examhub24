"""
Bulk-imports questions from a CSV file — addresses the "manually adding one question
at a time in admin is slow" pain point.

CSV columns (header row required), in this exact order:
    subject_id,question_text,option_a,option_b,option_c,option_d,correct_option,
    explanation,difficulty_level,marks,negative_marks,tags

- subject_id: numeric ID of an existing Subject (check /admin/exams/subject/ for IDs)
- correct_option: one of A, B, C, D
- difficulty_level: one of easy, medium, hard (defaults to medium if blank)
- marks / negative_marks: decimal numbers (default 1 / 0.25 if blank)
- tags: semicolon-separated tag names, e.g. "Percentage;Profit & Loss" (optional)

Usage:
    python manage.py import_questions_csv path/to/questions.csv

A sample template CSV can be generated with:
    python manage.py import_questions_csv --sample sample_questions.csv
"""
import csv
import decimal

from django.core.management.base import BaseCommand, CommandError

from exams.models import Subject
from questions.models import Question, QuestionTag

REQUIRED_COLUMNS = [
    'subject_id', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d',
    'correct_option', 'explanation', 'difficulty_level', 'marks', 'negative_marks', 'tags',
]


class Command(BaseCommand):
    help = 'Bulk-imports questions from a CSV file. Use --sample to generate a template file instead.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', nargs='?', type=str, help='Path to the CSV file to import.')
        parser.add_argument('--sample', type=str, help='Write a sample/template CSV to this path instead of importing.')

    def handle(self, *args, **options):
        if options.get('sample'):
            self._write_sample(options['sample'])
            return

        csv_path = options.get('csv_path')
        if not csv_path:
            raise CommandError('Please provide a CSV path, e.g. python manage.py import_questions_csv questions.csv')

        created, skipped, errors = 0, 0, []

        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            missing_cols = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
            if missing_cols:
                raise CommandError(f'CSV is missing required columns: {", ".join(missing_cols)}')

            for row_num, row in enumerate(reader, start=2):  # row 1 is the header
                try:
                    subject = Subject.objects.filter(pk=int(row['subject_id'])).first()
                    if not subject:
                        errors.append(f'Row {row_num}: subject_id {row["subject_id"]} not found — skipped.')
                        continue

                    correct_option = row['correct_option'].strip().upper()
                    if correct_option not in ('A', 'B', 'C', 'D'):
                        errors.append(f'Row {row_num}: correct_option must be A/B/C/D, got "{row["correct_option"]}" — skipped.')
                        continue

                    question, was_created = Question.objects.get_or_create(
                        subject=subject,
                        question_text=row['question_text'].strip(),
                        defaults={
                            'option_a': row['option_a'].strip(),
                            'option_b': row['option_b'].strip(),
                            'option_c': row['option_c'].strip(),
                            'option_d': row['option_d'].strip(),
                            'correct_option': correct_option,
                            'explanation': row.get('explanation', '').strip(),
                            'difficulty_level': (row.get('difficulty_level') or 'medium').strip().lower(),
                            'marks': decimal.Decimal(row['marks']) if row.get('marks') else decimal.Decimal('1'),
                            'negative_marks': decimal.Decimal(row['negative_marks']) if row.get('negative_marks') else decimal.Decimal('0.25'),
                        },
                    )

                    if was_created:
                        tag_names = [t.strip() for t in (row.get('tags') or '').split(';') if t.strip()]
                        for tag_name in tag_names:
                            tag, _ = QuestionTag.objects.get_or_create(name=tag_name)
                            question.tags.add(tag)
                        created += 1
                    else:
                        skipped += 1  # a question with identical subject+text already exists

                except (ValueError, decimal.InvalidOperation) as e:
                    errors.append(f'Row {row_num}: {e} — skipped.')

        self.stdout.write(self.style.SUCCESS(f'Imported {created} new question(s). Skipped {skipped} duplicate(s).'))
        if errors:
            self.stdout.write(self.style.WARNING(f'{len(errors)} row(s) had problems:'))
            for err in errors:
                self.stdout.write(f'  - {err}')

    def _write_sample(self, path):
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(REQUIRED_COLUMNS)
            writer.writerow([
                '1', 'What is 20% of 150?', '20', '25', '30', '35', 'C',
                '20% of 150 = 30.', 'easy', '1', '0.25', 'Percentage',
            ])
        self.stdout.write(self.style.SUCCESS(f'Sample CSV written to {path}. Fill it in and re-run without --sample.'))
