from auth_app.models import Notification, Challenge
from utils.words_cases import get_word_in_case
from django.db.models import Count, Q
from django.contrib.auth import get_user_model

User = get_user_model()

NOTIFICATION_TYPE_DATA = {
    "T": "transaction_data",
    "R": "report_data",
    "L": "like_data",
    "H": "challenge_data",
    "C": "comment_data",
    "W": "winner_data"
}


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


def get_amount_of_unread_notifications(user_id: int):
    notifications_amount = (User.objects.annotate(
        notifications_amount=Count('notifications', filter=Q(notifications__read=False)))
                   .filter(id=user_id).only('id').first().notifications_amount)
    return {"unread_notifications": notifications_amount}


def update_transaction_status_in_sender_notification(sender_id, transaction_id, status='R'):
    notification = Notification.objects.get(user_id=sender_id, type='T', object_id=transaction_id)
    data = notification.data
    data['status'] = status
    notification.data = data
    notification.save(update_fields=['data'])
    return notification


def get_notification_message_for_thanks_receiver(sender_tg_name, amount):
    amount_word = get_word_in_case(amount, "благодарность", "благодарности", "благодарностей")
    return "Вам пришла благодарность", f"{sender_tg_name} отправил(а) вам {amount} {amount_word}"


def get_notification_message_for_thanks_sender(receiver_tg_name, amount, status):
    theme = "Статус вашей благодарности изменился"
    return theme, f"""Текущий статус вашей благодарности 
        пользователю {receiver_tg_name} (сумма перевода - {amount}): {status}"""


def get_notification_message_for_created_challenge(challenge_name, creator_tg_name):
    theme = "Новый челлендж"
    text = f"{creator_tg_name} создала(а) новый челлендж под названием \"{challenge_name}\""
    return theme, text


def get_notification_message_for_thanks_sender_reaction(reaction_sender):
    return "Новая реакция", f"{reaction_sender} отреагировал на отправленную вами благодарность"


def get_notification_message_for_thanks_recipient_reaction(reaction_sender):
    return "Новая реакция", f"{reaction_sender} отреагировал на полученную вами благодарность"


def get_notification_message_for_challenge_reaction(reaction_sender, challenge_name):
    return "Новая реакция", f"{reaction_sender} отреагировал на челлендж \"{challenge_name}\""


def get_notification_message_for_comment_author_reaction(reaction_sender):
    return "Новая реакция", f"{reaction_sender} отреагировал на ваш комментарий"


def get_notification_message_for_thanks_sender_comment(comment_author):
    return "Новый комментарий", f"{comment_author} прокомментировал отправленную вами благодарность"


def get_notification_message_for_thanks_recipient_comment(comment_author):
    return "Новый комментарий", f"{comment_author} прокомментировал полученную вами благодарность"


def get_notification_message_for_challenge_comment(comment_author, challenge_name):
    return "Новый комментарий", f"{comment_author} прокомментировал челлендж \"{challenge_name}\""


def get_notification_message_for_challenge_author_get_report(report_author_name, challenge_name):
    return "Новый отчёт к челленджу", f"{report_author_name} отправил отчёт к челленджу \"{challenge_name}\""


def get_notification_message_for_challenge_winner(challenge_name):
    return "Победа в челлендже", f"Вы победили в челлендже \"{challenge_name}\""


def get_extended_pk_list_for_challenge_notifications(object_id, user):
    challenge = Challenge.objects.filter(pk=object_id).only('id', 'name', 'creator_id').first()
    winners_ids = (list(challenge.reports.select_related('participant')
                        .values_list('participant__user_participant_id', flat=True)))
    extended_ids_list = winners_ids + [challenge.creator_id]
    if user.id in set(extended_ids_list):
        extended_ids_list.remove(user.id)
    return challenge, extended_ids_list


def get_notification_data(transaction_instance):
    notification_data = {
        "sender_id": transaction_instance.sender_id
        if not transaction_instance.is_anonymous else None,
        "sender_tg_name": transaction_instance.sender.profile.tg_name
        if not transaction_instance.is_anonymous else None,
        "sender_photo": transaction_instance.sender.profile.get_thumbnail_photo_url
        if not transaction_instance.is_anonymous else None,
        "recipient_id": transaction_instance.recipient_id,
        "recipient_tg_name": transaction_instance.recipient.profile.tg_name,
        "recipient_photo": transaction_instance.recipient.profile.get_thumbnail_photo_url,
        "status": transaction_instance.status,
        "amount": int(transaction_instance.amount),
        "transaction_id": transaction_instance.pk,
        "income_transaction": False
    }
    return notification_data
