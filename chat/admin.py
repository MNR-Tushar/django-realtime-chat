from django.contrib import admin
from .models import Room, Message


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_private', 'created_at']
    list_filter = ['is_private']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

    def get_queryset(self, request):
      
        return super().get_queryset(request)

    def save_model(self, request, obj, form, change):
       
        if obj.slug.startswith('dm-'):
            obj.is_private = True
        super().save_model(request, obj, form, change)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['author', 'room', 'content', 'timestamp']
    list_filter = ['room', 'timestamp']
    search_fields = ['content', 'author__username']