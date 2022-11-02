from typing import Dict, List

from auth_app.models import Notification

FIELDS = (
    'id', 'type', 'object_id', 'theme',
    'text', 'read', 'created_at', 'updated_at'
)


def get_notification_list_by_user(user_id: int, offset: int, limit: int) -> List[Dict]:
    notifications = [notification for notification in Notification.objects
                     .filter(user_id=user_id)
                     .only(*FIELDS)
                     .order_by('-pk')
                     [offset * limit: offset * limit + limit]]
    notifications_list = []
    not_read_notifications = [notification for notification in notifications if not notification.read]
    if not_read_notifications:
        set_read_true_to_notification(not_read_notifications)
    for notification in notifications:
        notification_data = {
            "id": notification.id,
            "type": notification.type,
            "theme": notification.theme,
            "data": notification.data,
            "read": True,
            "created_at": notification.created_at,
            "updated_at": notification.updated_at
        }
        notifications_list.append(notification_data)
    return notifications_list


def set_read_true_to_notification(notifications):
    for notification in notifications:
        notification.read = True
    Notification.objects.bulk_update(notifications, fields=['read'])
