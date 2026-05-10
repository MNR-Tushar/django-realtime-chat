from django.db import models
from django.conf import settings


class Room(models.Model):

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)

    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='rooms', blank=True)
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_of_rooms',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    avatar = models.ImageField(upload_to='room_avatars/', blank=True, null=True)
    is_private = models.BooleanField(default=False)

    @classmethod
    def get_or_create_private(cls, user1, user2):
        rooms = cls.objects.filter(
            is_private=True,
            members=user1
        ).filter(members=user2)

        if rooms.exists():
            return rooms.first()

        slug = f'dm-{min(user1.id, user2.id)}-{max(user1.id, user2.id)}'

        room, created = cls.objects.get_or_create(
            slug=slug,
            defaults={
                'name': f'DM: {user1.username} & {user2.username}',
                'is_private': True,
            }
        )
        if created:
            room.members.add(user1, user2)
        return room

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Message(models.Model):
    """Chat message"""
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)

    # Reply feature
    reply_to = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='replies',
    )

    file = models.FileField(upload_to='chat_files/%Y/%m/', null=True, blank=True)
    file_type = models.CharField(
        max_length=20,
        choices=[('image', 'Image'), ('file', 'File')],
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f'{self.author.username}: {self.content[:40]}'


class JoinRequest(models.Model):
    """Request to join a private room"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='join_requests',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='join_requests',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('room', 'user')

    def __str__(self):
        return f'{self.user.username} → {self.room.name} [{self.status}]'


class Invitation(models.Model):
    """Invitation to join a private room"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='invitations',
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
    )
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_invitations',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('room', 'invited_user')

    def __str__(self):
        return f'{self.invited_by.username} invited {self.invited_user.username} → {self.room.name} [{self.status}]'


class EmojiReaction(models.Model):
    """Emoji reaction on a message"""
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='emoji_reactions'
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='emoji_reactions'
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_reactions'
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_reactions'
    )
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('message', 'from_user', 'emoji')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.from_user.username} reacted {self.emoji} to {self.to_user.username}'


class RoomActivity(models.Model):
    """Activity log for room events"""
    ACTIVITY_TYPES = [
        ('message', 'Message'),
        ('join', 'Join'),
        ('leave', 'Leave'),
        ('admin_transfer', 'Admin Transfer'),
        ('member_remove', 'Member Remove'),
        ('room_create', 'Room Create'),
        ('room_delete', 'Room Delete'),
        ('invitation_sent', 'Invitation Sent'),
        ('invitation_accept', 'Invitation Accept'),
        ('invitation_decline', 'Invitation Decline'),
        ('join_request', 'Join Request'),
        ('join_approve', 'Join Approve'),
        ('join_reject', 'Join Reject'),
    ]

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='room_activities'
    )
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField()
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='targeted_activities',
        help_text="User who is the target of this activity (e.g., removed member, new admin)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['room', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.activity_type} in {self.room.name}'