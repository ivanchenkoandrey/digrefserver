from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views

urlpatterns = [
    path('auth/', views.AuthView.as_view(), name='auth'),
    path('verify/', views.VerifyCodeView.as_view(),  name='verify'),
    path('user/profile/', views.ProfileView.as_view(), name='profile'),
    path('user/balance/', views.UserBalanceView.as_view(), name='balance'),
    path('user/stat/<int:period_id>/', views.get_user_stat_by_period, name='user_stat_by_period'),
    path('send-coins/', views.SendCoinView.as_view(), name='send_coins'),
    path('user/transactions/', views.TransactionsByUserView.as_view(), name='transactions_by_user'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
