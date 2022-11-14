from django.contrib.auth.views import LogoutView
from django.urls import path

from auth_app.accounts_views import views as account_views
from auth_app.auth_views import views as auth_views
from auth_app.challenge_reports_views import views as challenge_reports_views
from auth_app.challenges_views import views as challenges_views
from auth_app.comments_views import views as comments_views
from auth_app.contacts_views import views as contact_views
from auth_app.events_views import views as events_views
from auth_app.fcm_views import views as fcm_views
from auth_app.likes_views import views as likes_views
from auth_app.organization_views import views as organization_views
from auth_app.periods_views import views as periods_views
from auth_app.profile_views import views as profile_views
from auth_app.tags_views import views as tag_views
from auth_app.tg_bot_views import views as tg_bot_views
from auth_app.transaction_views import views as transaction_views
from auth_app.user_stat_views import views as stat_views
from auth_app.notification_views import views as notification_views
from . import views

urlpatterns = [
    # authentication
    path('auth/', auth_views.AuthView.as_view()),
    path('choose-organization/', auth_views.ChooseOrganizationViaAuthenticationView.as_view()),
    path('verify/', auth_views.VerifyCodeView.as_view()),

    # accounts
    path('emit/', account_views.EmitDistributionThanks.as_view()),

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
    path('update-profile-by-user/<int:pk>/', profile_views.UpdateProfileView.as_view()),
    path('update-profile-by-admin/<int:pk>/', profile_views.AdminUpdateProfileView.as_view()),
    path('update-contact-by-user/<int:pk>/', profile_views.UserUpdateContactView.as_view()),
    path('update-contact-by-admin/<int:pk>/', profile_views.AdminUpdateContactView.as_view()),
    path('create-contact-by-user/', contact_views.CreateContactByUserView.as_view()),
    path('create-contact-by-admin/', contact_views.CreateContactByAdminView.as_view()),
    path('delete-contact/<int:pk>/', contact_views.DeleteContactByAdmin.as_view()),
    path('create-few-contacts/', contact_views.CreateFewContactsByUser.as_view()),
    path('profile/<int:pk>/', views.GetProfileView.as_view()),
    path('get-user-profile-for-admin/<int:pk>/', views.GetProfileViewAdmin.as_view()),

    # challenges
    path('challenges/', challenges_views.ChallengeListView.as_view()),
    path('challenges/<int:pk>/', challenges_views.ChallengeDetailView.as_view()),
    path('challenge-winners/<int:pk>/', challenges_views.ChallengeWinnersList.as_view()),
    path('challenge-winners-reports/<int:pk>/', challenges_views.ChallengeWinnersReportsList.as_view()),
    path('challenge-contenders/<int:pk>/', challenges_views.ChallengeContendersList.as_view()),
    path('check-new-reports/', challenges_views.CheckIfNewReportsExistView.as_view()),
    path('challenge-result/<int:pk>/', challenges_views.GetUserChallengeReportView.as_view()),

    path('create-challenge/', challenges_views.CreateChallengeView.as_view()),
    path('create-challenge-report/', challenge_reports_views.CreateChallengeReportView.as_view()),
    path('check-challenge-report/<int:pk>/', challenge_reports_views.CheckChallengeReportView.as_view()),
    path('challenge-report/<int:pk>/', challenge_reports_views.ChallengeReportDetailAPIView.as_view()),

    # transactions
    path('send-coins/', transaction_views.SendCoinView.as_view()),
    path('cancel-transaction/<int:pk>/', transaction_views.CancelTransactionByUserView.as_view()),
    # path('check-transaction-by-controller/', transaction_views.VerifyOrCancelTransactionByControllerView.as_view()),
    path('user/transactions/', transaction_views.TransactionsByUserView.as_view()),
    path('user/transactions/<int:pk>/', transaction_views.SingleTransactionByUserView.as_view()),
    path('user/transactions-by-period/<int:period_id>/', transaction_views.get_user_transaction_list_by_period),

    # events
    path('feed/', events_views.EventListView.as_view()),
    path('events/', events_views.FeedView.as_view()),
    path('events/transactions/', events_views.TransactionFeedView.as_view()),
    path('events/transactions/<int:pk>/', events_views.EventTransactionDetailView.as_view()),
    path('events/winners/', events_views.ReportFeedView.as_view()),
    path('events/challenges/', events_views.ChallengeFeedView.as_view()),

    # notifications
    path('notifications/', notification_views.NotificationList.as_view()),
    path('notifications/<int:pk>/', notification_views.MarkNotificationAsReadView.as_view()),
    path('notifications/unread/amount/', notification_views.GetUnreadNotificationsCount.as_view()),

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
    path('organizations/<int:pk>/', organization_views.OrganizationDetailView.as_view()),
    path('organizations/<int:pk>/image/', organization_views.UpdateOrganizationLogoView.as_view()),
    path('send-code-to-change-organization/', organization_views.SendCodeToChangeOrganizationView.as_view()),
    path('change-organization/', organization_views.ChangeOrganizationView.as_view()),
    path('user/organizations/', organization_views.GetUserOrganizations.as_view()),

    # tags
    path('send-coins-settings/', tag_views.TagList.as_view()),
    path('tags/<int:pk>/', tag_views.TagDetailView.as_view()),
    path('reasons/', tag_views.ReasonListView.as_view()),

    # tg bot views
    path('tg-get-user-token/', tg_bot_views.GetUserToken.as_view()),
    path('tg-admin-analytics/', tg_bot_views.GetAnalyticsAdmin.as_view()),
    path('tg-export/', tg_bot_views.ExportUserTransactions.as_view()),
    path('tg-balance/', tg_bot_views.ExportUserBalance.as_view()),

    # fcm
    path('set-fcm-token/', fcm_views.SetFCMToken.as_view()),
    path('remove-fcm-token/', fcm_views.RemoveFCMToken.as_view()),

    path('burn-thanks/', views.BurnThanksView.as_view()),
    path('burn-income-thanks/', views.BurnIncomeThanksView.as_view()),
    path('create-user-stats/', stat_views.CreateUserStats.as_view()),
    path('logout/', LogoutView.as_view()),
    # comments
    path('create-comment/', comments_views.CreateCommentView.as_view()),
    path('update-comment/<int:pk>/', comments_views.UpdateCommentView.as_view()),
    path('delete-comment/<int:pk>/', comments_views.DeleteCommentView.as_view()),
    path('get-comments/', comments_views.CommentListAPIView.as_view()),
    # likes
    path('press-like/', likes_views.PressLikeView.as_view()),
    path('get-likes-by-transaction/', likes_views.LikesListAPIView.as_view()),
    path('get-likes/', likes_views.LikesListAPIView.as_view()),
    path('get-likes-by-user/', likes_views.LikesUserListAPIView.as_view()),
    # statistics
    path('get-transaction-statistics/', transaction_views.TransactionStatisticsAPIView.as_view()),
    path('get-likes-comments-statistics/', transaction_views.TransactionStatisticsAPIView.as_view())
]
