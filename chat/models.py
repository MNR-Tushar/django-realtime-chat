from django.db import models
from django.conf import settings


class Room(models.Model):
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='rooms', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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

    class Meta:
        ordering = ['timestamp']  

    def __str__(self):
        return f'{self.author.username}: {self.content[:40]}'