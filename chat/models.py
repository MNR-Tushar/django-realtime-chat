from django.db import models
from django.conf import settings


class Room(models.Model):
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='rooms', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    is_private = models.BooleanField(default=False) 
    
    @classmethod 
    def get_or_create_private(cls, user1, user2): 
        
        rooms = cls.objects.filter( is_private=True, members=user1 ).filter(members=user2)
         
        if rooms.exists(): 
            return rooms.first() 
        
        slug = f'dm-{min(user1.id,user2.id)}-{max(user1.id,user2.id)}' 
        room = cls.objects.create( name=f'DM: {user1.username} & {user2.username}', slug=slug, is_private=True )
        
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
    
    file = models.FileField( upload_to='chat_files/%Y/%m/', null=True, blank=True ) 
    file_type = models.CharField( max_length=20, choices=[('image','Image'),('file','File')], null=True, blank=True )

    class Meta:
        ordering = ['timestamp']  

    def __str__(self):
        return f'{self.author.username}: {self.content[:40]}'
    
    

