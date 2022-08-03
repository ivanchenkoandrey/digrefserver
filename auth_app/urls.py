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
    path('cancel-transaction/<int:pk>/', views.CancelTransactionByUserView.as_view(), name='cancel-transaction'),
    path('check-transaction-by-controller/', views.VerifyOrCancelTransactionByControllerView.as_view(),
         name='check-transaction-by-controller'),
    path('user/transactions/', views.TransactionsByUserView.as_view(), name='transactions_by_user'),
    path('user/transactions/<int:pk>/', views.SingleTransactionByUserView.as_view(), name='single_user_transaction'),
    path('user/transactions-by-period/<int:period_id>/', views.get_user_transaction_list_by_period,
         name='user_transactions_by_period'),
    path('search-user/', views.SearchUserView.as_view(), name='search_user'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
