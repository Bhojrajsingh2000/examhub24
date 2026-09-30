from django.conf import settings
from django.db import models


class Discussion(models.Model):
    question = models.ForeignKey('questions.Question', on_delete=models.CASCADE, related_name='discussions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='discussion_comments')
    comment = models.TextField(max_length=2000)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='liked_discussions')
    created_at = models.DateTimeField(auto_now_add=True)
    is_flagged = models.BooleanField(default=False, help_text='Flagged for admin review (spam/abuse report).')

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user} on Q{self.question_id}: {self.comment[:40]}"

    @property
    def like_count(self):
        return self.likes.count()

    def is_reply(self):
        return self.parent_id is not None
