from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.index, name='index'),
    path('room/<slug:room_slug>/', views.room, name='room'),
    path('dm/<str:username>/', views.direct_message, name='dm'),
    path('room/<slug:room_slug>/upload/', views.upload_file, name='upload_file'),

    # ── Join Request URLs ──────────────────────────────────
    path('room/<slug:room_slug>/join-request/', views.request_join, name='request_join'),
    path('room/<slug:room_slug>/join-request/cancel/', views.cancel_join_request, name='cancel_join_request'),
    path('join-request/<int:request_id>/<str:action>/', views.handle_join_request, name='handle_join_request'),
    path('pending-requests/', views.pending_requests_panel, name='pending_requests_panel'),
]