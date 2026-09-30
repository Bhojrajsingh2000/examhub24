from django.conf import settings
from django.db import models


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        RESULT = 'result', 'Result Declared'
        NEW_TEST = 'new_test', 'New Test Available'
        ANNOUNCEMENT = 'announcement', 'Announcement'
        PAYMENT = 'payment', 'Payment Update'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.ANNOUNCEMENT)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} -> {self.user}"

    @staticmethod
    def send(user, title, message, notification_type=NotificationType.ANNOUNCEMENT):
        """Convenience helper other apps can call, e.g. Notification.send(user, 'Result Declared', '...')."""
        return Notification.objects.create(user=user, title=title, message=message, notification_type=notification_type)
