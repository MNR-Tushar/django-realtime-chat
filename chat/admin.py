from django.contrib import admin
from .models import *


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_private', 'admin', 'created_at']
    list_filter = ['is_private']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    raw_id_fields = ['admin', 'members']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('admin')

    def save_model(self, request, obj, form, change):

        if obj.slug.startswith('dm-'):
            obj.is_private = True
        super().save_model(request, obj, form, change)

    def delete_model(self, _request, obj):
        # Delete related objects manually to avoid FK issues
        obj.messages.all().delete()
        obj.join_requests.all().delete()
        obj.invitations.all().delete()

        # Disable FK checks for this deletion (SQLite workaround)
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys = OFF')
        obj.delete()
        cursor.execute('PRAGMA foreign_keys = ON')

    def delete_queryset(self, request, queryset):
        # Bulk delete with manual cleanup
        for obj in queryset:
            self.delete_model(request, obj)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['author', 'room', 'content', 'timestamp']
    list_filter = ['room', 'timestamp']
    search_fields = ['content', 'author__username']
    
@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'room__name']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'room')


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ['invited_by', 'invited_user', 'room', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['invited_by__username', 'invited_user__username', 'room__name']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('invited_by', 'invited_user', 'room')


@admin.register(EmojiReaction)
class EmojiReactionAdmin(admin.ModelAdmin):
    list_display = ['from_user', 'to_user', 'room', 'message', 'emoji', 'created_at', 'updated_at']
    list_filter = ['emoji', 'created_at']
    search_fields = ['from_user__username', 'to_user__username', 'message__content', 'room__name']
    raw_id_fields = ['from_user', 'to_user', 'message', 'room']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('from_user', 'to_user', 'message', 'room')