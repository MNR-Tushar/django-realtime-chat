from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):

    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=200,blank=True, null=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username

    def get_last_seen_text(self):
        """Return human-readable last seen text like '5 min ago'"""
        from django.utils import timezone
        if self.is_online:
            return "online"
        if not self.last_seen:
            return "never"

        now = timezone.now()
        diff = now - self.last_seen

        if diff.days > 365:
            return f"{diff.days // 365}y ago"
        if diff.days > 30:
            return f"{diff.days // 30}mo ago"
        if diff.days > 0:
            return f"{diff.days}d ago"
        if diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        if diff.seconds > 60:
            return f"{diff.seconds // 60}min ago"
        return "just now"

