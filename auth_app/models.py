from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import CITextField, CICharField
from django.db import models
from django.db.models import Q, F, ExpressionWrapper
from django.db.models.fields import DateTimeField
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
    organization_type = CICharField(max_length=1, choices=OrganizationTypes.choices, verbose_name='Тип организации')
    top_id = models.ForeignKey('self', on_delete=models.CASCADE, related_name='pride', verbose_name='Юр.лицо')
    parent_id = models.ForeignKey('self', on_delete=models.CASCADE, related_name='children', null=True,
                                  verbose_name='Входит в', blank=True)
    photo = models.ImageField(blank=True, null=True, upload_to='organizations', verbose_name='Фотография')

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'organizations'


class EmployeeStatus(models.TextChoices):
    OFFICE = 'O', 'В офисе'
    DISTANT = 'D', 'Удалённо'
    HOLIDAY = 'H', 'Отпуск'
    SICK = 'S', 'На больничном'


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, related_name='profileorganization',
                                     null=True,
                                     verbose_name='Юр.лицо', blank=True)
    department = models.ForeignKey(Organization, on_delete=models.SET_NULL, related_name='profiledepartment', null=True,
                                   verbose_name='Подразделение', blank=True)
    tg_id = CICharField(max_length=20, verbose_name='Идентификатор пользователя Telegram')
    tg_name = CICharField(max_length=40, blank=True, null=True, verbose_name='Имя пользователя Telegram')
    photo = models.ImageField(blank=True, null=True, upload_to='users_photo/', verbose_name='Фотография')
    hired_at = models.DateField(null=True, blank=True, verbose_name='Работает с')
    fired_at = models.DateField(null=True, blank=True, verbose_name='Не работает с')
    surname = CITextField(blank=True, null=True, default='', verbose_name='Фамилия')
    first_name = CITextField(blank=True, null=True, verbose_name='Имя')
    middle_name = CITextField(blank=True, null=True, verbose_name='Отчество')
    nickname = CITextField(blank=True, null=True, verbose_name='Псевдоним')
    status = models.CharField(max_length=1, choices=EmployeeStatus.choices,
                              verbose_name='Статус сотрудника', null=True, blank=True)
    timezone = models.PositiveSmallIntegerField(verbose_name='Разница во времени с МСК', null=True, blank=True)
    date_of_birth = models.DateField(verbose_name='Дата рождения', null=True, blank=True)
    job_title = CICharField(max_length=100, verbose_name='Должность', null=True, blank=True)

    def get_photo_url(self):
        if self.photo:
            return f"{self.photo.url}"
        return None

    @property
    def get_surname(self):
        if self.surname:
            return self.surname
        return None

    @property
    def get_first_name(self):
        if self.first_name:
            return self.first_name
        return None

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}

    def __str__(self):
        return str(self.user)

    class Meta:
        db_table = 'profiles'


class Contact(models.Model):
    class ContactTypes(models.TextChoices):
        EMAIL = '@', 'Email'
        TG = 'T', 'Telegram'
        PHONE = 'P', 'Телефон'

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='contacts', verbose_name='Контакты')
    contact_type = models.CharField(max_length=1, choices=ContactTypes.choices, verbose_name='Вид контакта')
    contact_id = CITextField(verbose_name='Адрес или номер')
    confirmed = models.BooleanField(verbose_name='Подтверждено')

    class Meta:
        db_table = 'contacts'

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}


class UserRole(models.Model):
    class Roles(models.TextChoices):
        ADMIN = 'A', 'Администратор'
        CONTROLLER = 'C', 'Контролер'
        MANAGER = 'M', 'Распорядитель'

    role = models.CharField(max_length=1, choices=Roles.choices, verbose_name='Роль')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='privileged', verbose_name='Пользователь')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='privileged', null=True,
                                     verbose_name='Подразделение', blank=True)

    def __str__(self):
        return str(self.user)

    class Meta:
        db_table = 'user_roles'


class TransactionStatus(models.TextChoices):
    WAITING = 'W', 'Ожидает подтверждения'
    APPROVED = 'A', 'Одобрено'
    DECLINED = 'D', 'Отклонено'
    INGRACE = 'G', 'Ожидает'
    READY = 'R', 'Выполнена'
    CANCELLED = 'C', 'Отменена'


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


class CustomTransactionQueryset(models.QuerySet):
    """
    Объект, инкапсулирующий в себе логику кастомных запросов к БД
    в рамках менеджера objects в инстансах модели Transaction
    """

    def filter_by_user(self, current_user):
        """
        Возвращает список транзакций пользователя
        """
        queryset = (self
                    .select_related('sender__profile', 'recipient__profile', 'reason_def')
                    .prefetch_related('tags')
                    .filter((Q(sender=current_user) | (Q(recipient=current_user) & ~(Q(status__in=['G', 'C', 'D']))))))
        return self.add_expire_to_cancel_field(queryset).order_by('-updated_at')

    def filter_to_use_by_controller(self):
        """
        Возвращает список транзакций со статусом 'Ожидает подтверждения'
        """
        queryset = (self
                    .select_related('sender__profile', 'recipient__profile', 'reason_def')
                    .prefetch_related('tags')
                    .filter(status='W'))
        return self.add_expire_to_cancel_field(queryset).order_by('-created_at')

    def filter_by_period(self, current_user, period):
        """
        Возвращает список транзакций пользователя, совершенных в рамках конкретного периода
        """

        queryset = (self
                    .select_related('sender__profile', 'recipient__profile', 'reason_def')
                    .prefetch_related('tags')
                    .filter((Q(sender=current_user) | Q(recipient=current_user)) &
                            Q(created_at__gte=period.start_date) & Q(created_at__lte=period.end_date)
                            ))
        return self.add_expire_to_cancel_field(queryset).order_by('-updated_at')

    @staticmethod
    def add_expire_to_cancel_field(queryset):
        """
        Возвращает список транзакций, к которому добавлено поле формата даты, где указывается,
        когда истекает возможность отменить транзакцию со стороны пользователя
        """
        return queryset.annotate(expire_to_cancel=ExpressionWrapper(
            F('created_at') + timedelta(seconds=settings.GRACE_PERIOD), output_field=DateTimeField()))


class Transaction(models.Model):
    objects = CustomTransactionQueryset.as_manager()

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outcomes', verbose_name='Отправитель')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes', verbose_name='Получатель')
    transaction_class = models.CharField(max_length=1, choices=TransactionClass.choices, verbose_name='Вид транзакции')
    amount = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='Количество')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Время обновления состояния', null=True, blank=True)
    status = models.CharField(max_length=1, choices=TransactionStatus.choices, verbose_name='Состояние транзакции')
    reason = CITextField(verbose_name='Обоснование', null=True, blank=True)
    grace_timeout = models.DateTimeField(verbose_name='Время окончания периода возможной отмены', null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL,
                                     related_name='organization_public_transactions',
                                     null=True, blank=True, verbose_name='Согласующая организация')
    period = models.ForeignKey('Period', on_delete=models.CASCADE, related_name='transactions', verbose_name='Период',
                               null=True, blank=True)
    is_anonymous = models.BooleanField(verbose_name='Отправитель скрыт', null=True, blank=True)
    is_public = models.BooleanField(verbose_name='Публичность', null=True, blank=True)
    scope = models.ForeignKey(Organization, on_delete=models.SET_NULL, related_name='scope_public_transactions',
                              null=True,
                              blank=True,
                              verbose_name='Уровень публикации')
    photo = models.ImageField(blank=True, null=True, upload_to='transactions', verbose_name='Фотография')
    reason_def = models.ForeignKey('Reason', on_delete=models.PROTECT, verbose_name='Типовое обоснование', null=True,
                                   blank=True)

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}

    def get_photo_url(self):
        if self.photo:
            return f"{self.photo.url}"
        return None

    def __str__(self):
        date = self.updated_at.strftime('%d-%m-%Y %H:%M:%S')
        return (f"to: {self.recipient} "
                f"class: {self.transaction_class} "
                f"status: {self.status} "
                f"updated: {date}")

    class Meta:
        db_table = 'transactions'
        constraints = [
            models.CheckConstraint(
                name='check_sender_is_not_recipient',
                check=(~Q(sender=F('recipient')) | ~(Q(transaction_class='T') | Q(transaction_class='R')))
            )
        ]


# наверно нужен указатель на запись на итоговый TransactionState. но пока можно считать, что запись в states будет только одна - либо подтв., либо отказ

class TransactionState(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='states',
                                    verbose_name='Транзакция')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')
    controller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='revised', verbose_name='Контролер')
    status = models.CharField(max_length=1, choices=TransactionStatus.choices, verbose_name='Состояние транзакции')
    reason = CITextField(verbose_name='Обоснование (отклонения)', null=True, blank=True)

    class Meta:
        db_table = 'transaction_states'


class AccountTypes(models.TextChoices):
    INCOME = 'I', 'Заработанные'
    DISTR = 'D', 'Для раздачи'
    FROZEN = 'F', 'Ожидает подтверждения'
    SYSTEM = 'S', 'Системный'  # системный, один, для organization [ROOT] и владелец администратор
    BURNT = 'B', 'Сгоревшие'  # системный, один, для organization [ROOT] и владелец администратор
    BONUS = 'O', 'Для расчета премий'  # для organization [ROOT|TOP], user - контролер для этой organization или вышестоящей
    MARKET = 'P', 'Покупки'  # для маркетплейсов
    TREASURY = 'T', 'Эмитент'  # источник для transaction [EMIT]


class Account(models.Model):
    account_type = models.CharField(max_length=1, choices=AccountTypes.choices, verbose_name='Тип счета')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts', verbose_name='Владелец')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='accounts',
                                     verbose_name='Подразделение', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='Количество')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Время обновления')
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}

    def __str__(self):
        return str(self.owner)

    class Meta:
        db_table = 'accounts'


class Period(models.Model):
    start_date = models.DateField(verbose_name='С')
    end_date = models.DateField(verbose_name='По')
    name = CITextField(verbose_name='Название')  # например Июнь 2022 или 3й квартал 2022
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, related_name='periods',
                                     verbose_name='Организация', null=True,
                                     blank=True)  # поддерево организаций, к которым относится период.

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'periods'


class UserStat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stats', verbose_name='Пользователь')
    period = models.ForeignKey(Period, on_delete=models.CASCADE, related_name='stats', verbose_name='Период')
    bonus = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name='Премия')  # получается извне
    income_at_start = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                          verbose_name='Остаток на начало периода')  # account [INCOME]
    income_at_end = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                        verbose_name='Остаток на конец периода')  # account [INCOME]
    income_exp = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                     verbose_name='Получено за стаж работы')  # account [INCOME] <- transaction [EXP]
    income_thanks = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                        verbose_name='Получено в качестве благодарности')
    # account [INCOME] <- transaction [THANKS]
    income_used_for_bonus = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                                verbose_name='Использовано для распределения премий')
    # account [INCOME] -> transaction [BONUS]
    income_used_for_thanks = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                                 verbose_name='Использовано своих для благодарности')
    # account [INCOME] -> transaction [THANKS]
    income_declined = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                          verbose_name='Сгоревшие (отклоненные транзакции из своих)')
    # account [INCOME] -> transaction [THANKS][DECLINED]
    distr_initial = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                        verbose_name='Получено для распределения')
    # account [DISTR] <- transaction [DISTR]
    distr_redist = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                       verbose_name='Получено для распределения')
    # account [DISTR] <- transaction [REDIST]
    distr_burnt = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                      verbose_name='Сгоревшие как неиспользованные')
    # account [DISTR] -> transaction [BURNING]
    distr_thanks = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                       verbose_name='Использовано распределяемых')
    # account [DISTR] -> transaction [THANKS]
    distr_declined = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                         verbose_name='Сгоревшие (отклоненные транзакции из распределяемых)')

    # account [DISTR] -> transaction [THANKS][DECLINED]

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}

    class Meta:
        db_table = 'user_stats'


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


class EventObjectTypes(models.TextChoices):
    TRANSACTION = 'T', 'Транзакция'
    QUEST = 'Q', 'Запрос (челлендж, квест)'


class EventRecordTypes(models.TextChoices):
    TRANS_STATUS = 'S', 'Статус транзакции'
    LIKE_ITEM = 'L', 'Лайк'
    COMMENT_ITEM = 'C', 'Комментарий'


class EventTypes(models.Model):
    # id - идентификатор
    name = CITextField()
    object_type = models.CharField(max_length=1, choices=EventObjectTypes.choices, verbose_name='Тип объекта',
                                   null=True, blank=True)
    record_type = models.CharField(max_length=1, choices=EventRecordTypes.choices, verbose_name='Тип записи о событии',
                                   null=True, blank=True)
    is_personal = models.BooleanField(verbose_name='Относится к пользователю')
    has_scope = models.BooleanField(verbose_name='Имеет область видимости')

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}

    class Meta:
        db_table = 'event_types'


# 'Входящая транзакция'  Transaction NULL 1 0
# 'Исходящая транзакция отклонена' Transaction TransactionStatus  1 0
# 'Исходящая транзакция одобрена' Transaction TransactionStatus 1 0
# 'Новая публичная транзакция' Transaction NULL 0 1
# 'Новая транзакция для согласования' Transaction NULL 0 1
# 'Новый комментарий' Transaction TransComment 1 1
# 'Новый лайк' Transaction TransLike 1 1


class Event(models.Model):
    # id: идентификатор - создается автоматически
    # тип события - транзакция, лайк и тп
    event_type = models.ForeignKey(EventTypes, on_delete=models.PROTECT, verbose_name='Тип события')
    # объект, с которым произошло событие
    event_object_id = models.IntegerField(null=True, blank=True)
    # объект, описывающий событие
    event_record_id = models.IntegerField(null=True, blank=True)
    # таймстамп когда событие произошло / обновилось
    time = models.DateTimeField(verbose_name='Время события')
    # область видимости (организация)
    scope = models.ForeignKey(Organization, on_delete=models.SET_NULL, verbose_name='Область видимости', null=True,
                              blank=True)
    # пользователь - адресат события
    user = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name='Пользователь', null=True, blank=True)

    class Meta:
        db_table = 'events'

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}


class Tag(models.Model):
    created_at = models.DateTimeField(verbose_name='Время создания', auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name='Пользователь, создавший ценность',
                                   null=True, blank=True, related_name='tag_created_by')
    updated_at = models.DateTimeField(verbose_name='Время обновления', auto_now=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name='Пользователь, изменивший ценность',
                                   null=True, blank=True, related_name='tag_updated_by')
    flags = models.CharField(max_length=10, default="A", verbose_name="Флаги состояния", null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     verbose_name='Подразделение (область видимости)', null=True, blank=True)
    time_from = models.DateTimeField(verbose_name='Начало периода действия', null=True, blank=True)
    time_to = models.DateTimeField(verbose_name='Окончание периода действия', null=True, blank=True)
    name = CICharField(max_length=100, verbose_name="Отображаемый текст тега")
    info = models.TextField(verbose_name="Пояснительный текст тега", null=True, blank=True)
    pict = models.ImageField(upload_to='tags', verbose_name="Пиктограмма", null=True, blank=True)

    def get_pict_url(self):
        if self.pict:
            return f"{self.pict.url}"
        return None

    class Meta:
        db_table = 'tags'
        verbose_name = "Ценности"


class Reason(models.Model):
    created_at = models.DateTimeField(verbose_name='Время создания', auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='reason_created_by',
                                   verbose_name='Пользователь, добавивший типовое обоснование', null=True, blank=True)
    updated_at = models.DateTimeField(verbose_name='Время обновления', auto_now=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='reason_updated_by',
                                   verbose_name='Пользователь, изменивший типовое обоснование', null=True, blank=True)
    flags = models.CharField(max_length=10, default="A", verbose_name="Флаги состояния", null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     verbose_name='Подразделение (область видимости)', null=True, blank=True)
    time_from = models.DateTimeField(verbose_name='Начало периода действия', null=True, blank=True)
    time_to = models.DateTimeField(verbose_name='Окончание периода действия', null=True, blank=True)
    data = CITextField(verbose_name="Текст типового обоснования")
    tags = models.ManyToManyField(Tag, related_name='reasons', through='ReasonByTag')

    class Meta:
        db_table = 'reasons'
        verbose_name = "Типовые обоснования"


class ReasonByTag(models.Model):
    created_at = models.DateTimeField(verbose_name='Время назначения', auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='reason_by_tag_created_by',
                                   verbose_name='Пользователь, назначивший типовое обоснование ценности', null=True,
                                   blank=True)
    updated_at = models.DateTimeField(verbose_name='Время изменения', auto_now=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='reason_by_tag_updated_by',
                                   verbose_name='Пользователь, изменивший назначение типового обоснования ценности',
                                   null=True, blank=True)
    flags = models.CharField(max_length=10, default="A", verbose_name="Флаги состояния", null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     verbose_name='Подразделение (область видимости)', null=True, blank=True)
    time_from = models.DateTimeField(verbose_name='Начало периода действия', null=True, blank=True)
    time_to = models.DateTimeField(verbose_name='Окончание периода действия', null=True, blank=True)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, verbose_name='Ценность')
    reason = models.ForeignKey(Reason, on_delete=models.CASCADE, verbose_name='Типовое обоснование')

    class Meta:
        db_table = 'reasons_by_tags'
        verbose_name = "Назначения типовых обоснований ценностям"


class ObjectTag(models.Model):
    created_at = models.DateTimeField(verbose_name='Время назначения', auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='object_tag_created_by',
                                   verbose_name='Пользователь, назначивший ценность', null=True, blank=True)
    updated_at = models.DateTimeField(verbose_name='Время отключения', auto_now=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='object_tag_updated_by',
                                   verbose_name='Пользователь, отключивший ценность', null=True, blank=True)
    flags = models.CharField(max_length=10, default="A", verbose_name="Флаги состояния", null=True, blank=True)
    tagged_object = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='tags', verbose_name='Объект')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='objecttags', verbose_name='Ценность')

    class Meta:
        db_table = 'object_tags'
        verbose_name = "Назначения ценностей объектам"


class TagLink(models.Model):
    created_at = models.DateTimeField(verbose_name='Время назначения', auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='tag_link_created_by',
                                   verbose_name='Пользователь, назначивший синоним ценности', null=True, blank=True)
    updated_at = models.DateTimeField(verbose_name='Время изменения', auto_now=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='tag_link_updated_by',
                                   verbose_name='Пользователь, изменивший назначение синонима ценности', null=True,
                                   blank=True)
    flags = models.CharField(max_length=10, default="A", verbose_name="Флаги состояния", null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     verbose_name='Подразделение (область видимости)', null=True, blank=True)
    time_from = models.DateTimeField(verbose_name='Начало периода действия', null=True, blank=True)
    time_to = models.DateTimeField(verbose_name='Окончание периода действия', null=True, blank=True)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, verbose_name='Ценность', related_name='tag_link')
    tag_basic = models.ForeignKey(Tag, on_delete=models.CASCADE,
                                  verbose_name='Ценность - основной синоним', related_name='tag_link_basic')

    class Meta:
        db_table = 'tag_links'
        verbose_name = "Синонимы ценностей"


@receiver(post_save, sender=User)
def create_auth_token(instance: User, created: bool, **kwargs):
    if created:
        Token.objects.create(user=instance)


@receiver(post_save, sender=Profile)
def create_income_account(instance: Profile, created: bool, **kwargs):
    if created:
        Account.objects.create(
            owner=instance.user,
            account_type='I',
            organization=instance.department,
            amount=0
        )


@receiver(post_save, sender=Profile)
def create_frozen_account(instance: Profile, created: bool, **kwargs):
    if created:
        Account.objects.create(
            owner=instance.user,
            account_type='F',
            organization=instance.department,
            amount=0
        )


@receiver(post_save, sender=Profile)
def create_frozen_account(instance: Profile, created: bool, **kwargs):
    if created:
        Account.objects.create(
            owner=instance.user,
            account_type='D',
            organization=instance.department,
            amount=0
        )


@receiver(post_save, sender=User)
def create_user_stat(instance: User, created: bool, **kwargs):
    if created:
        from utils.current_period import get_current_period
        period = get_current_period()
        if period:
            UserStat.objects.create(
                user=instance,
                period=period
            )
