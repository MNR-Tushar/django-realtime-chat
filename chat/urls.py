from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.index, name='index'),
    path('room/<slug:room_slug>/', views.room, name='room'),
    path('dm/<str:username>/', views.direct_message, name='dm'), 
    #path('users/', views.user_list, name='user_list'),
]