"""
Tests for the question discussion module (comments, threaded replies, likes, flagging).

Run with:
    python manage.py test discussion
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from exams.models import Exam, ExamCategory, Subject
from questions.models import Question

from .models import Discussion

User = get_user_model()


class DiscussionTests(TestCase):
    def setUp(self):
        cache.clear()  # post_comment is rate-limited; avoid cross-test contamination
        self.user = User.objects.create_user(username='ivan', password='pass12345', email='ivan@example.com')
        self.other_user = User.objects.create_user(username='julia', password='pass12345', email='julia@example.com')
        self.client.force_login(self.user)

        category = ExamCategory.objects.create(name='Banking', slug='banking')
        exam = Exam.objects.create(category=category, name='SBI PO', slug='sbi-po')
        subject = Subject.objects.create(exam=exam, name='English')
        self.question = Question.objects.create(
            subject=subject, question_text='Fill in the blank: She ___ to school.',
            option_a='go', option_b='goes', option_c='going', option_d='gone', correct_option='B',
        )

    def test_post_top_level_comment(self):
        self.client.post(reverse('discussion:post_comment', args=[self.question.id]), {'comment': 'Why is it "goes" not "go"?'})
        self.assertEqual(Discussion.objects.filter(question=self.question, parent__isnull=True).count(), 1)

    def test_post_reply_links_to_parent(self):
        top = Discussion.objects.create(question=self.question, user=self.user, comment='Doubt here')
        self.client.post(reverse('discussion:post_comment', args=[self.question.id]), {
            'comment': 'Because subject is third-person singular.', 'parent_id': top.id,
        })
        reply = Discussion.objects.get(parent=top)
        self.assertEqual(reply.comment, 'Because subject is third-person singular.')

    def test_empty_comment_is_ignored(self):
        self.client.post(reverse('discussion:post_comment', args=[self.question.id]), {'comment': '   '})
        self.assertEqual(Discussion.objects.count(), 0)

    def test_thread_page_shows_posted_comments(self):
        Discussion.objects.create(question=self.question, user=self.user, comment='A visible comment')
        response = self.client.get(reverse('discussion:question_discussion', args=[self.question.id]))
        self.assertContains(response, 'A visible comment')

    def test_like_toggle_on_then_off(self):
        comment = Discussion.objects.create(question=self.question, user=self.other_user, comment='Helpful tip')
        url = reverse('discussion:toggle_like', args=[comment.id])

        response = self.client.post(url)
        self.assertEqual(response.json(), {'liked': True, 'like_count': 1})

        response = self.client.post(url)
        self.assertEqual(response.json(), {'liked': False, 'like_count': 0})

    def test_flag_comment_marks_it_for_review(self):
        comment = Discussion.objects.create(question=self.question, user=self.other_user, comment='Suspicious content')
        self.client.post(reverse('discussion:flag_comment', args=[comment.id]))
        comment.refresh_from_db()
        self.assertTrue(comment.is_flagged)

    def test_posting_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse('discussion:post_comment', args=[self.question.id]), {'comment': 'Anonymous doubt'})
        self.assertEqual(response.status_code, 302)  # redirected to login
        self.assertEqual(Discussion.objects.count(), 0)
