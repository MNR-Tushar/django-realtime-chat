from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.index, name='index'),
    path('room/<slug:room_slug>/', views.room, name='room'),
    path('dm/<str:username>/', views.direct_message, name='dm'),
    path('room/<slug:room_slug>/upload/', views.upload_file, name='upload_file'),

    # ── Room Settings ──────────────────────────────────────────────
    path('room/<slug:room_slug>/settings/', views.room_settings, name='room_settings'),
    path('room/<slug:room_slug>/remove-member/', views.remove_member, name='remove_member'),
    path('room/<slug:room_slug>/leave/', views.leave_group, name='leave_group'),

    # ── Message Pagination ──────────────────────────────────────────
    path('room/<slug:room_slug>/older-messages/', views.load_older_messages, name='load_older_messages'),

    # ── Join Request URLs ──────────────────────────────────────────
    path('room/<slug:room_slug>/join-request/', views.request_join, name='request_join'),
    path('room/<slug:room_slug>/join-request/cancel/', views.cancel_join_request, name='cancel_join_request'),
    path('join-request/<int:request_id>/<str:action>/', views.handle_join_request, name='handle_join_request'),
    path('pending-requests/', views.pending_requests_panel, name='pending_requests_panel'),

    # ── Private Room & Invitation URLs ──────────────────────────────
    path('create-room/', views.create_private_room, name='create_private_room'),
    path('room/<slug:room_slug>/invite/', views.invite_to_room, name='invite_to_room'),
    path('invitation/<int:invitation_id>/<str:action>/', views.handle_invitation, name='handle_invitation'),
    path('my-invitations/', views.my_invitations, name='my_invitations'),
    
    # ── User Profile URLs ───────────────────────────────────────────
    path('user/<str:username>/profile/', views.user_profile, name='user_profile'),
]