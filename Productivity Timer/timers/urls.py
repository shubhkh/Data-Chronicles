from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'timers'

urlpatterns = [
    path('', views.home, name='home'),
    path('stopwatch/', views.stopwatch, name='stopwatch'),
    path('countdown/', views.countdown, name='countdown'),
    path('pomodoro/', views.pomodoro, name='pomodoro'),
    path('report/', views.report, name='report'),
    path('sessions/', views.sessions_history, name='sessions'),
    path('tasks/', views.tasks, name='tasks'),
    path('challenges/', views.challenges, name='challenges'),
    path('challenges/new/', views.challenge_new, name='challenge_new'),
    path('challenges/<int:pk>/accept/', views.challenge_accept, name='challenge_accept'),
    path('challenges/mine/<int:pk>/', views.challenge_detail, name='challenge_detail'),
    path('challenges/mine/<int:pk>/edit/', views.challenge_edit, name='challenge_edit'),
    path('challenges/mine/<int:pk>/delete/', views.challenge_delete, name='challenge_delete'),
    path('challenges/mine/<int:pk>/log/<str:day>/', views.challenge_entry, name='challenge_entry'),
    path('tasks/add/', views.task_add, name='task_add'),
    path('tasks/<int:pk>/toggle/', views.task_toggle, name='task_toggle'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),
    path('profile/', views.profile, name='profile'),
    path('register/', views.register, name='register'),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='timers/login.html',
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(next_page='timers:home'),
        name='logout',
    ),
    path('api/sessions/', views.log_session, name='log_session'),
]
