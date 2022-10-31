from auth_app.models import Notification
from utils.words_cases import get_word_in_case


def get_notification_message_for_thanks_receiver(sender_tg_name, amount):
    amount_word = get_word_in_case(amount, "благодарность", "благодарности", "благодарностей")
    return "Вам пришла благодарность", f"{sender_tg_name} отправил(а) вам {amount} {amount_word}"


def get_notification_message_for_thanks_sender(receiver_tg_name, amount, success=True):
    theme = "Статус вашей благодарности изменился"
    if success:
        amount_word = get_word_in_case(amount, "благодарность", "благодарности", "благодарностей")
        return theme, f"{receiver_tg_name} получил от вас {amount} {amount_word}"
    amount_word = get_word_in_case(amount, "благодарности", "благодарностей", "благодарностей")
    return theme, f"Отменен перевод {amount} {amount_word} для пользователя {receiver_tg_name}"


def create_notification(user_id, object_id, _type, theme, text, read=False):
    return Notification.objects.create(
        user_id=user_id,
        object_id=object_id,
        type=_type,
        theme=theme,
        text=text,
        read=read
    )
