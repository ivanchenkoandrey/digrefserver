from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views
from auth_app.admin_views import views as admin_views
from auth_app.auth_views import views as auth_views
from auth_app.transaction_views import views as transaction_views

urlpatterns = [
    # authentication
    path('auth/', auth_views.AuthView.as_view(), name='auth'),
    path('verify/', auth_views.VerifyCodeView.as_view(),  name='verify'),
    # profile
    path('user/profile/', views.ProfileView.as_view(), name='profile'),
    path('user/balance/', views.UserBalanceView.as_view(), name='balance'),
    path('user/stat/<int:period_id>/', views.get_user_stat_by_period, name='user_stat_by_period'),
    path('search-user/', views.SearchUserView.as_view(), name='search_user'),
    # transactions
    path('send-coins/', transaction_views.SendCoinView.as_view(), name='send_coins'),
    path('cancel-transaction/<int:pk>/', transaction_views.CancelTransactionByUserView.as_view(),
         name='cancel-transaction'),
    path('check-transaction-by-controller/', transaction_views.VerifyOrCancelTransactionByControllerView.as_view(),
         name='check-transaction-by-controller'),
    path('user/transactions/', transaction_views.TransactionsByUserView.as_view(), name='transactions_by_user'),
    path('user/transactions/<int:pk>/', transaction_views.SingleTransactionByUserView.as_view(),
         name='single_user_transaction'),
    path('user/transactions-by-period/<int:period_id>/', transaction_views.get_user_transaction_list_by_period,
         name='user_transactions_by_period'),
    # for admin
    path('set-anonymous-mode/', admin_views.set_anonymous_mode, name='set_anonymous_mode'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
