from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=200,blank=True, null=True)
    is_online = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username

