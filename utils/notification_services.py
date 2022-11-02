from auth_app.models import Notification
from utils.words_cases import get_word_in_case


NOTIFICATION_TYPE_DATA = {
    "T": "transaction_data",
    "R": "winner_data",
    "L": "like_data",
    "H": "challenge_data",
    "C": "comment_data"
}


def get_notification_message_for_thanks_receiver(sender_tg_name, amount):
    amount_word = get_word_in_case(amount, "благодарность", "благодарности", "благодарностей")
    return "Вам пришла благодарность", f"{sender_tg_name} отправил(а) вам {amount} {amount_word}"


def get_notification_message_for_thanks_sender(receiver_tg_name, amount, status):
    theme = "Статус вашей благодарности изменился"
    return theme, f"""Текущий статус вашей благодарности 
        пользователю {receiver_tg_name} (сумма перевода - {amount}): {status}"""


def create_notification(user_id, object_id, _type, theme, text, read=False, data='', from_user=None):
    return Notification.objects.create(
        user_id=user_id,
        from_user=from_user,
        object_id=object_id,
        type=_type,
        theme=theme,
        text=text,
        read=read,
        data=data
    )


def update_transaction_status_in_sender_notification(sender_id, transaction_id):
    notification = Notification.objects.get(user_id=sender_id, type='T', object_id=transaction_id)
    data = notification.data
    data['status'] = 'R'
    notification.data = data
    notification.save(update_fields=['data'])
    return notification
