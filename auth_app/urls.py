from django.urls import path
from . import views

urlpatterns = [
    path('auth/', views.AuthView.as_view(), name='auth'),
    path('verify/', views.VerifyCodeView.as_view(),  name='verify'),
    path('user/profile/', views.ProfileView.as_view(), name='profile'),
]
