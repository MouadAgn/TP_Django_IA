from django.urls import path
from django.shortcuts import render
from . import views

def profile(request):
    template = request.GET.get('template', 'profile.html')
    return render(request, f'users/templates/{template}')

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('profile/', profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),
]