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
    path('auth/', auth_views.AuthView.as_view()),
    path('verify/', auth_views.VerifyCodeView.as_view()),
    # profile
    path('user/profile/', views.ProfileView.as_view()),
    path('user/balance/', views.UserBalanceView.as_view()),
    path('user/stat/<int:period_id>/', views.get_user_stat_by_period),
    path('search-user/', views.SearchUserView.as_view()),
    path('users-list/', views.UsersList.as_view()),
    path('update-profile-image/<int:pk>/', profile_views.UpdateProfileImageView.as_view()),
    path('create-employee/', profile_views.CreateEmployeeView.as_view()),
    path('create-user-role/', profile_views.CreateUserRoleView.as_view()),
    path('remove-user-role/<int:pk>/', profile_views.DeleteUserRoleView.as_view()),
    path('get-user-roles/', profile_views.UserRoleListView.as_view()),
    path('update-profile-by-user/<int:pk>/', profile_views.UserUpdateProfileView.as_view()),
    path('update-profile-by-admin/<int:pk>/', profile_views.AdminUpdateProfileView.as_view()),
    path('update-contact-by-user/<int:pk>/', profile_views.UserUpdateContactView.as_view()),
    path('update-contact-by-admin/<int:pk>/', profile_views.AdminUpdateContactView.as_view()),
    # transactions
    path('send-coins/', transaction_views.SendCoinView.as_view()),
    path('cancel-transaction/<int:pk>/', transaction_views.CancelTransactionByUserView.as_view()),
    path('check-transaction-by-controller/', transaction_views.VerifyOrCancelTransactionByControllerView.as_view()),
    path('user/transactions/', transaction_views.TransactionsByUserView.as_view()),
    path('user/transactions/<int:pk>/', transaction_views.SingleTransactionByUserView.as_view()),
    path('user/transactions-by-period/<int:period_id>/', transaction_views.get_user_transaction_list_by_period),
    # events
    path('feed/', events_views.EventListView.as_view()),
    # periods
    path('periods/', periods_views.PeriodListView.as_view()),
    path('create-period/', periods_views.CreatePeriodView.as_view()),
    path('get-current-period/', periods_views.get_current_period),
    path('get-period-by-date/', periods_views.get_period_by_date),
    path('get-periods/', periods_views.get_periods),
    # organizations
    path('create-root-organization/', organization_views.CreateRootOrganization.as_view()),
    path('create-department/', organization_views.CreateDepartmentView.as_view()),
    path('root-organizations/', organization_views.RootOrganizationListView.as_view()),
    path('get-organization-departments/', organization_views.DepartmentsListView.as_view()),

    path('logout/', LogoutView.as_view()),
]
