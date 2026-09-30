"""
Seeds the database with realistic demo data so the whole ExamHub24 platform can be
tested end-to-end without manually filling the admin panel first.

Usage:
    python manage.py seed_demo_data

Safe to run multiple times — uses get_or_create everywhere, so it won't create duplicates.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import StudentProfile
from analytics.models import PerformanceAnalytics  # noqa: F401 (imported for completeness/reference)
from current_affairs.models import CurrentAffair
from exams.models import Exam, ExamCategory, Subject
from mock_tests.models import MockTest, TestQuestion, TestSeries
from questions.models import Question, QuestionTag
from subscriptions.models import Coupon, Plan

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds demo data (exams, questions, mock test, plans, current affairs, test users) for testing.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding demo data for ExamHub24...')

        student = self._create_demo_student()
        category, exam, subject = self._create_exam_content()
        tags = self._create_tags()
        questions = self._create_questions(subject, tags)
        series, test = self._create_test_series(exam, questions)
        self._create_plans()
        self._create_coupon()
        self._create_current_affairs()

        self.stdout.write(self.style.SUCCESS('\nDemo data seeded successfully!\n'))
        self.stdout.write('-' * 60)
        self.stdout.write(f'Demo student login  -> username: demo_student   password: DemoPass@123')
        self.stdout.write(f'Mock test ready      -> "{test.title}" ({test.total_questions} questions)')
        self.stdout.write(f'Visit /mock-tests/ to see the "{series.title}" series and start the test.')
        self.stdout.write('Try coupon code WELCOME20 (20% off) at checkout on /subscriptions/.')
        self.stdout.write('-' * 60)

    def _create_demo_student(self):
        student, created = User.objects.get_or_create(
            username='demo_student',
            defaults={
                'email': 'demo_student@example.com',
                'full_name': 'Demo Student',
                'phone_number': '9999900001',
                'is_verified': True,
            },
        )
        if created:
            student.set_password('DemoPass@123')
            student.save()
            StudentProfile.objects.get_or_create(user=student)
            self.stdout.write(self.style.SUCCESS('Created demo student user.'))
        return student

    def _create_exam_content(self):
        category, _ = ExamCategory.objects.get_or_create(
            slug='banking',
            defaults={'name': 'Banking', 'description': 'Bank PO, Clerk and related exams.', 'is_active': True},
        )
        exam, _ = Exam.objects.get_or_create(
            slug='ibps-po',
            defaults={
                'category': category,
                'name': 'IBPS PO',
                'description': 'Institute of Banking Personnel Selection — Probationary Officer exam.',
                'exam_date': date.today() + timedelta(days=90),
                'is_active': True,
            },
        )
        subject, _ = Subject.objects.get_or_create(
            exam=exam, name='Quantitative Aptitude',
            defaults={'description': 'Numerical ability and mathematics section.'},
        )
        self.stdout.write(self.style.SUCCESS('Created exam category, exam, and subject.'))
        return category, exam, subject

    def _create_tags(self):
        names = ['Percentage', 'Time & Work', 'Simple Interest', 'Averages', 'Profit & Loss']
        tags = []
        for name in names:
            tag, _ = QuestionTag.objects.get_or_create(name=name)
            tags.append(tag)
        return tags

    def _create_questions(self, subject, tags):
        sample_questions = [
            {
                'question_text': 'If 20% of a number is 50, what is the number?',
                'option_a': '200', 'option_b': '250', 'option_c': '300', 'option_d': '150',
                'correct_option': 'B', 'explanation': '20% of x = 50  =>  x = 50 / 0.20 = 250.',
                'tag': 'Percentage',
            },
            {
                'question_text': 'A can complete a work in 10 days and B in 15 days. Working together, how many days will they take?',
                'option_a': '5 days', 'option_b': '6 days', 'option_c': '7 days', 'option_d': '8 days',
                'correct_option': 'B', 'explanation': '1/10 + 1/15 = 1/6, so together they take 6 days.',
                'tag': 'Time & Work',
            },
            {
                'question_text': 'Find the simple interest on Rs. 5000 at 8% per annum for 3 years.',
                'option_a': 'Rs. 1000', 'option_b': 'Rs. 1200', 'option_c': 'Rs. 1500', 'option_d': 'Rs. 1350',
                'correct_option': 'B', 'explanation': 'SI = (P*R*T)/100 = (5000*8*3)/100 = 1200.',
                'tag': 'Simple Interest',
            },
            {
                'question_text': 'The average of 5 numbers is 20. If one number is excluded, the average becomes 18. Find the excluded number.',
                'option_a': '24', 'option_b': '26', 'option_c': '28', 'option_d': '30',
                'correct_option': 'C', 'explanation': 'Sum of 5 = 100, sum of 4 = 72, excluded number = 100-72 = 28.',
                'tag': 'Averages',
            },
            {
                'question_text': 'A shopkeeper buys an item for Rs. 400 and sells it for Rs. 460. Find the profit percentage.',
                'option_a': '10%', 'option_b': '12%', 'option_c': '15%', 'option_d': '20%',
                'correct_option': 'C', 'explanation': 'Profit = 60, Profit% = (60/400)*100 = 15%.',
                'tag': 'Profit & Loss',
            },
            {
                'question_text': 'What is 15% of 200?',
                'option_a': '20', 'option_b': '25', 'option_c': '30', 'option_d': '35',
                'correct_option': 'C', 'explanation': '15% of 200 = 30.',
                'tag': 'Percentage',
            },
            {
                'question_text': '12 workers can finish a job in 8 days. How many days will 16 workers take?',
                'option_a': '5 days', 'option_b': '6 days', 'option_c': '7 days', 'option_d': '4 days',
                'correct_option': 'B', 'explanation': '12*8 = 16*x  =>  x = 6 days.',
                'tag': 'Time & Work',
            },
            {
                'question_text': 'Find the compound-equivalent... (simple version) SI on Rs. 8000 at 5% for 2 years.',
                'option_a': 'Rs. 700', 'option_b': 'Rs. 800', 'option_c': 'Rs. 900', 'option_d': 'Rs. 1000',
                'correct_option': 'B', 'explanation': 'SI = (8000*5*2)/100 = 800.',
                'tag': 'Simple Interest',
            },
            {
                'question_text': 'The average weight of 4 friends is 60 kg. A fifth friend weighing 70 kg joins. Find the new average.',
                'option_a': '61 kg', 'option_b': '62 kg', 'option_c': '63 kg', 'option_d': '64 kg',
                'correct_option': 'B', 'explanation': '(4*60 + 70)/5 = 310/5 = 62 kg.',
                'tag': 'Averages',
            },
            {
                'question_text': 'A book is sold at a 10% loss for Rs. 900. Find its cost price.',
                'option_a': 'Rs. 950', 'option_b': 'Rs. 980', 'option_c': 'Rs. 1000', 'option_d': 'Rs. 1050',
                'correct_option': 'C', 'explanation': 'CP * 0.9 = 900  =>  CP = 1000.',
                'tag': 'Profit & Loss',
            },
        ]

        tag_map = {t.name: t for t in tags}
        created_questions = []
        for q in sample_questions:
            question, created = Question.objects.get_or_create(
                subject=subject,
                question_text=q['question_text'],
                defaults={
                    'option_a': q['option_a'], 'option_b': q['option_b'],
                    'option_c': q['option_c'], 'option_d': q['option_d'],
                    'correct_option': q['correct_option'],
                    'explanation': q['explanation'],
                    'difficulty_level': Question.Difficulty.MEDIUM,
                    'marks': 1, 'negative_marks': 0.25,
                },
            )
            if created:
                question.tags.add(tag_map[q['tag']])
            created_questions.append(question)

        self.stdout.write(self.style.SUCCESS(f'Created {len(created_questions)} sample questions.'))
        return created_questions

    def _create_test_series(self, exam, questions):
        series, _ = TestSeries.objects.get_or_create(
            exam=exam, title='IBPS PO Free Mock Series',
            defaults={'description': 'Free demo test series for IBPS PO.', 'is_free': True, 'price': 0, 'validity_days': 365},
        )
        test, created = MockTest.objects.get_or_create(
            series=series, title='Quantitative Aptitude — Mock Test 1',
            defaults={
                'duration_minutes': 15,
                'negative_marking': True,
                'instructions': 'This is a demo test with 10 questions. Negative marking of 0.25 applies per wrong answer.',
                'is_active': True,
            },
        )
        if created:
            for i, question in enumerate(questions, start=1):
                TestQuestion.objects.get_or_create(test=test, question=question, defaults={'question_order': i})
            self.stdout.write(self.style.SUCCESS('Created free test series and mock test with 10 questions.'))
        return series, test

    def _create_plans(self):
        plans_data = [
            {'name': 'Silver Monthly', 'price': 149, 'duration_days': 30, 'features': 'All free tests, 20 premium mock tests, Email support'},
            {'name': 'Gold Quarterly', 'price': 399, 'duration_days': 90, 'features': 'Unlimited mock tests, Study material, Priority email support'},
            {'name': 'Platinum Yearly', 'price': 1299, 'duration_days': 365, 'features': 'Everything in Gold, Video lectures, Priority support'},
        ]
        for p in plans_data:
            Plan.objects.get_or_create(name=p['name'], defaults={
                'price': p['price'], 'duration_days': p['duration_days'], 'features': p['features'], 'is_active': True,
            })
        self.stdout.write(self.style.SUCCESS('Created subscription plans.'))

    def _create_coupon(self):
        Coupon.objects.get_or_create(code='WELCOME20', defaults={
            'discount_type': Coupon.DiscountType.PERCENTAGE,
            'discount_value': 20,
            'is_active': True,
        })
        self.stdout.write(self.style.SUCCESS('Created sample coupon: WELCOME20 (20% off).'))

    def _create_current_affairs(self):
        items = [
            {'title': 'RBI Keeps Repo Rate Unchanged', 'category': CurrentAffair.Category.ECONOMY,
             'content': 'The Reserve Bank of India kept the repo rate unchanged in its latest monetary policy review, citing stable inflation trends.'},
            {'title': 'India Wins Bilateral Series', 'category': CurrentAffair.Category.SPORTS,
             'content': 'The Indian cricket team secured a series victory in a closely contested bilateral series.'},
            {'title': 'New Government Scheme Launched for MSMEs', 'category': CurrentAffair.Category.NATIONAL,
             'content': 'The government announced a new credit support scheme aimed at boosting the MSME sector.'},
        ]
        for item in items:
            CurrentAffair.objects.get_or_create(
                title=item['title'],
                defaults={'content': item['content'], 'date': date.today(), 'category': item['category'], 'is_published': True},
            )
        self.stdout.write(self.style.SUCCESS('Created sample current affairs articles.'))
