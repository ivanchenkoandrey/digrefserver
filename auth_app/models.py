from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import CITextField, CICharField
from django.db import models
from django.db.models import Q, F
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

User = get_user_model()


class Organization(models.Model):
    class OrganizationTypes(models.TextChoices):
        ROOT = 'R', 'Ведущая компания группы'
        TOP = 'T', 'Юридическое лицо со своим премиальным фондом'
        FIRM = 'С', 'Юридическое лицо'
        DEPT = 'D', 'Подразделение'
        MARKET = 'М', 'Маркетплейс'

    name = CITextField()
    organization_type = CICharField(max_length=1, choices=OrganizationTypes.choices, verbose_name='Вид контакта')
    top_id = models.ForeignKey('self', on_delete=models.CASCADE, related_name='pride', verbose_name='Юр.лицо')
    parent_id = models.ForeignKey('self', on_delete=models.CASCADE, related_name='children', null=True,
                                  verbose_name='Входит в')

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, related_name='profileorganization',
                                     null=True,
                                     verbose_name='Юр.лицо')
    department = models.ForeignKey(Organization, on_delete=models.SET_NULL, related_name='profiledepartment', null=True,
                                   verbose_name='Подразделение')
    tg_id = CICharField(max_length=20, verbose_name='Идентификатор пользователя Telegram')
    tg_name = CICharField(max_length=20, blank=True, null=True, verbose_name='Имя пользователя Telegram')
    photo = models.ImageField(blank=True, null=True, upload_to='users_photo/', verbose_name='Фотография')
    hired_at = models.DateField(null=True, blank=True, verbose_name='Работает с')
    surname = CITextField(blank=True, default='', verbose_name='Фамилия')
    first_name = CITextField(blank=True, null=True, verbose_name='Имя')
    middle_name = CITextField(blank=True, null=True, verbose_name='Отчество')
    nickname = CITextField(blank=True, null=True, verbose_name='Псевдоним')

    def __str__(self):
        return str(self.user)


class Contact(models.Model):
    class ContactTypes(models.TextChoices):
        EMAIL = '@', 'Email'
        TG = 'T', 'Telegram'
        PHONE = 'P', 'Телефон'

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='contacts', verbose_name='Контакты')
    contact_type = models.CharField(max_length=1, choices=ContactTypes.choices, verbose_name='Вид контакта')
    contact_id = CITextField(verbose_name='Адрес или номер')
    confirmed = models.BooleanField(verbose_name='Подтверждено')


class UserRole(models.Model):
    class Roles(models.TextChoices):
        ADMIN = 'A', 'Администратор'
        CONTROLLER = 'С', 'Контролер'
        MANAGER = 'M', 'Распорядитель'

    role = models.CharField(max_length=1, choices=Roles.choices, verbose_name='Роль')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='privileged', verbose_name='Пользователь')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='privileged', null=True,
                                     verbose_name='Подразделение')


class TransactionStatus(models.TextChoices):
    WAITING = 'W', 'Ожидает подтверждения'
    APPROVED = 'A', 'Одобрено'
    DECLINED = 'D', 'Отклонено'


class TransactionClass(models.TextChoices):
    THANKS = 'T', 'Благодарность'  # всегда в account [INCOME] из account [DISTR|INCOME(если разрешено настройкой)]
    EXP = 'X', 'За стаж работы'  # один раз в начале периода, идет в account [INCOME] c account [SYSTEM], его баланс не проверяем
    DISTR = 'D', 'Для распределения'  # один раз в начале периода на каждого сотрудника, идет в account [DISTR] c account [SYSTEM], его баланс не проверяем
    # плюс по команде администратора в account [DISTR] менеджера с account [SYSTEM], баланс проверяем
    REDIST = 'R', 'Для перераспределения'  # между менеджерами, идет в account [DISTR] из account [DISTR|INCOME(если разрешено настройкой)]
    BURNING = 'B', 'Сгорание'  # в конце периода, только из account [DISTR] только в account [BURNT]
    BONUS = 'O', 'Для расчета премии'  # в конце периода, только из account [INCOME, только в account [BONUS]
    PURCHASE = 'P', 'Покупка'  # при покупках в внутреннем маркетплейсе, только из account [INCOMDE] только в account [MARKET]
    EMIT = 'E', 'Эмитирование'  # только для account [SYSTEM] из account [TREASURY], вброс баллов в систему, возможно как погашение отрицательного баланса account [SYSTEM], источника
    CASH = 'С', 'Погашение'  # источник account [BONUS|MARKET|BURNING], получатель account [TREASURY]
    # в моб.приложении сейчас создаются только Transaction [THANKS]
    # возможно потом добавятся BONUS, REDIST, PURCHASE


class Transaction(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outcomes', verbose_name='Отправитель')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes', verbose_name='Получатель')
    transaction_class = models.CharField(max_length=1, choices=TransactionClass.choices, verbose_name='Вид транзакции')
    amount = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='Количество')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Время обновления состояния', null=True)
    status = models.CharField(max_length=1, choices=TransactionStatus.choices, verbose_name='Состояние транзакции')
    reason = CITextField(verbose_name='Обоснование')

    def __str__(self):
        date = self.updated_at.strftime('%d-%m-%Y %H:%M:%S')
        return f"to: {self.recipient} class: {self.transaction_class} status: {self.status} updated: {date}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        account = Account.objects.filter(owner=self.recipient, account_type='I').first()
        states = self.states.all()
        if account is not None:
            if self.status == 'W':
                account.frozen += self.amount
            elif self.status == 'A' and len(states) == 1:
                account.frozen -= self.amount
                account.amount += self.amount
            elif self.status == 'A' and len(states) > 1:
                account.amount += self.amount
            elif self.status == 'D' and len(states) == 1:
                account.frozen -= self.amount
            elif self.status == 'D' and len(states) > 1:
                account.amount -= self.amount
            account.transaction = self
            account.save()
        else:
            Account.objects.create(
                owner=self.recipient,
                account_type='I',
                organization=self.recipient.profile.department,
                amount=0,
                frozen=self.amount,
                transaction=self
            )

    class Meta:
        constraints = [
            models.CheckConstraint(
                name='check_sender_is_not_recipient',
                check=~Q(sender=F('recipient'))
            )
        ]


# наверно нужен указатель на запись на итоговый TransactionState. но пока можно считать, что запись в states будет только одна - либо подтв., либо отказ

class TransactionState(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='states',
                                    verbose_name='Транзакция')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')
    controller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='revised', verbose_name='Контролер')
    status = models.CharField(max_length=1, choices=TransactionStatus.choices, verbose_name='Состояние транзакции')
    reason = CITextField(verbose_name='Обоснование (отклонения)', null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        transaction = self.transaction
        transaction.status = self.status
        transaction.save()


class AccountTypes(models.TextChoices):
    INCOME = 'I', 'Заработанные'
    DISTR = 'D', 'Для раздачи'
    SYSTEM = 'S', 'Системный'  # системный, один, для organization [ROOT] и владелец администратор
    BURNT = 'B', 'Сгоревшие'  # системный, один, для organization [ROOT] и владелец администратор
    BONUS = 'O', 'Для расчета премий'  # для organization [ROOT|TOP], user - контролер для этой organization или вышестоящей
    MARKET = 'P', 'Покупки'  # для маркетплейсов
    TREASURY = 'T', 'Эмитент'  # источник для transaction [EMIT]


class Account(models.Model):
    account_type = models.CharField(max_length=1, choices=AccountTypes.choices, verbose_name='Тип счета')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts', verbose_name='Владелец')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='accounts',
                                     verbose_name='Подразделение', null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='Количество')
    frozen = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='Ожидает подтверждения')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Время обновления')
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return str(self.owner)


class Period(models.Model):
    start_date = models.DateField(verbose_name='С')
    end_date = models.DateField(verbose_name='По')
    name = CITextField(verbose_name='Название')  # например Июнь 2022 или 3й квартал 2022

    def __str__(self):
        return self.name


class UserStat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stats', verbose_name='Пользователь')
    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name='stats', verbose_name='Период')
    bonus = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='Премия')  # получается извне
    income_at_start = models.DecimalField(max_digits=10, decimal_places=0,
                                          verbose_name='Остаток на начало периода')  # account [INCOME]
    income_at_end = models.DecimalField(max_digits=10, decimal_places=0,
                                        verbose_name='Остаток на конец периода')  # account [INCOME]
    income_exp = models.DecimalField(max_digits=10, decimal_places=0,
                                     verbose_name='Получено за стаж работы')  # account [INCOME] <- transaction [EXP]
    income_thanks = models.DecimalField(max_digits=10, decimal_places=0,
                                        verbose_name='Получено в качестве благодарности')
    # account [INCOME] <- transaction [THANKS]
    income_used_for_bonus = models.DecimalField(max_digits=10, decimal_places=0,
                                                verbose_name='Использовано для распределения премий')
    # account [INCOME] -> transaction [BONUS]
    income_used_for_thanks = models.DecimalField(max_digits=10, decimal_places=0,
                                                 verbose_name='Использовано своих для благодарности')
    # account [INCOME] -> transaction [THANKS]
    income_declined = models.DecimalField(max_digits=10, decimal_places=0,
                                          verbose_name='Сгоревшие (отклоненные транзакции из своих)')
    # account [INCOME] -> transaction [THANKS][DECLINED]
    distr_initial = models.DecimalField(max_digits=10, decimal_places=0,
                                        verbose_name='Получено для распределения')
    # account [DISTR] <- transaction [DISTR]
    distr_redist = models.DecimalField(max_digits=10, decimal_places=0,
                                       verbose_name='Получено для распределения')
    # account [DISTR] <- transaction [REDIST]
    distr_burnt = models.DecimalField(max_digits=10, decimal_places=0,
                                      verbose_name='Сгоревшие как неиспользованные')
    # account [DISTR] -> transaction [BURNING]
    distr_thanks = models.DecimalField(max_digits=10, decimal_places=0,
                                       verbose_name='Использовано распределяемых')
    # account [DISTR] -> transaction [THANKS]
    distr_declined = models.DecimalField(max_digits=10, decimal_places=0,
                                         verbose_name='Сгоревшие (отклоненные транзакции из распределяемых)')
    # account [DISTR] -> transaction [THANKS][DECLINED]


# /user/<id>/balance :
# /user/<id>/stat/<period_id> :
# - account.amount - только для текущего периода, для прошлых - всего получено баллов :
#       income_at_start + income_exp + income_thanks для левого и distr_initial + distr_redist для правого
# - стартовое количество - income_at_start + income_exp для левого, distr_initial для правого
# - количество полученных - income_thanks, distr_redist
# - количество отправленных - income_used_for_thanks и distr_thanks
# - количество на согласовании (account.frozen) - для обоих столбцов для текущего периода, для прошлых строки нет !
# - количество аннулированных - income_declined, distr_declined
# - только для прошлых периодов : количество сгоревших для правого столбца distr_burnt
#       и количество использованных для расчета премий для левого income_used_for_bonus
# - только для прошлых периодов : сумма премии bonus
# - только для прошлых периодов : остаток баллов на конец периода income_at_end

@receiver(post_save, sender=User)
def create_auth_token(instance, created, **kwargs):
    if created:
        Token.objects.create(user=instance)
