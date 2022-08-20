from django.contrib.auth.views import LogoutView
from django.urls import path

from auth_app.auth_views import views as auth_views
from auth_app.events_views import views as events_views
from auth_app.organization_views import views as organization_views
from auth_app.periods_views import views as periods_views
from auth_app.profile_views import views as profile_views
from auth_app.transaction_views import views as transaction_views
from . import views

urlpatterns = [
    # authentication
    path('auth/', auth_views.AuthView.as_view(), name='auth'),
    path('verify/', auth_views.VerifyCodeView.as_view(),  name='verify'),
    # profile
    path('user/profile/', views.ProfileView.as_view(), name='profile'),
    path('user/balance/', views.UserBalanceView.as_view(), name='balance'),
    path('user/stat/<int:period_id>/', views.get_user_stat_by_period, name='user_stat_by_period'),
    path('search-user/', views.SearchUserView.as_view(), name='search_user'),
    path('users-list/', views.UsersList.as_view(), name='users-list'),
    path('update-profile-image/<int:pk>/', profile_views.UpdateProfileImageView.as_view(),
         name='update_profile_image'),
    path('create-employee/', profile_views.CreateEmployeeView.as_view()),
    path('create-user-role/', profile_views.CreateUserRoleView.as_view()),
    path('remove-user-role/<int:pk>/', profile_views.DeleteUserRoleView.as_view()),
    path('get-user-roles/', profile_views.UserRoleListView.as_view()),
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
    # events
    path('feed/', events_views.EventListView.as_view(), name='feed'),
    # periods
    path('periods/', periods_views.PeriodListView.as_view(), name='periods'),
    path('create-period/', periods_views.CreatePeriodView.as_view(), name='create_period'),
    path('get-current-period/', periods_views.get_current_period, name='get_current_period'),
    path('get-period-by-date/', periods_views.get_period_by_date, name='get_period_by_date'),
    path('get-periods/', periods_views.get_periods, name='get_periods'),
    # organizations
    path('create-root-organization/', organization_views.CreateRootOrganization.as_view(),
         name='create_root_organization'),
    path('create-department/', organization_views.CreateDepartmentView.as_view(),
         name='create_department'),
    path('root-organizations/', organization_views.RootOrganizationListView.as_view()),
    path('get-organization-departments/', organization_views.DepartmentsListView.as_view()),

    path('logout/', LogoutView.as_view(), name='logout'),
]
