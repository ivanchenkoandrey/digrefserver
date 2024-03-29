from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.fields import CITextField, CICharField
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from auth_app.managers import *
from utils.thumbnail_link import get_thumbnail_link

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
    head_of_department = models.ForeignKey(User, related_name='heads', null=True, blank=True, on_delete=models.SET_NULL,
                                           verbose_name='Руководитель организации(подразделения)')

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}

    def __str__(self):
        return self.name

    @property
    def get_photo_url(self):
        if self.photo:
            return self.photo.url

    @property
    def get_thumbnail_photo_url(self):
        if self.photo:
            return f"{get_thumbnail_link(self.photo.url)}"

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
    tg_id = CICharField(max_length=20, verbose_name='Идентификатор пользователя Telegram', null=True, blank=True)
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
    main_email = CICharField(max_length=255, default='', blank=True, verbose_name='Основной адрес электронной почты')

    def get_photo_url(self):
        if self.photo:
            return f"{self.photo.url}"
        return None

    @property
    def get_thumbnail_photo_url(self):
        if self.photo:
            return f"{get_thumbnail_link(self.photo.url)}"

    @property
    def get_surname(self):
        if self.surname:
            return self.surname
        return ''

    @property
    def get_middle_name(self):
        if self.middle_name:
            return self.middle_name
        return ''

    @property
    def get_first_name(self):
        if self.first_name:
            return self.first_name
        return ''

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
    TO_CHALLENGE = 'H', 'Для взноса в челлендж'
    AWARD_FROM_CHALLENGE = 'W', 'Награда из челленджа'
    RETURN_FROM_CHALLENGE = 'F', 'Возврат из челленджа'


class Transaction(models.Model):
    objects = CustomTransactionQueryset.as_manager()

    sender = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='outcomes', verbose_name='Отправитель')
    sender_account = models.ForeignKey('Account', on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='sendertransactions', verbose_name='Счёт отправителя')
    recipient = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='incomes', verbose_name='Получатель')
    recipient_account = models.ForeignKey('Account', on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='recipienttransactions', verbose_name='Счёт получателя')
    from_challenge = models.ForeignKey('Challenge', on_delete=models.SET_NULL, related_name='fromtransactions',
                                       null=True, blank=True, verbose_name='От челленджа')
    to_challenge = models.ForeignKey('Challenge', on_delete=models.SET_NULL, related_name='totransactions',
                                     null=True, blank=True, verbose_name='Челленджу')
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

    is_commentable = models.BooleanField(default=True,
                                         verbose_name="Разрешение на добавление/изменение/удаления комментариев")
    challenge_report = models.ForeignKey('ChallengeReport', null=True, blank=True, related_name='rewards',
                                         on_delete=models.SET_NULL, verbose_name='Отчёт о выполнении челленджа')
    comments = GenericRelation('Comment')
    likes = GenericRelation('Like')

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}

    def get_photo_url(self):
        if self.photo:
            return f"{self.photo.url}"

    @property
    def get_thumbnail_photo_url(self):
        if self.photo:
            return f"{get_thumbnail_link(self.photo.url)}"

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


class TransactionState(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='states',
                                    verbose_name='Транзакция')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')
    controller = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE,
                                   related_name='revised', verbose_name='Контролер')
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
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts',
                              null=True, blank=True, verbose_name='Владелец')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='accounts',
                                     verbose_name='Подразделение', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='Количество')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Время обновления')
    transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    challenge = models.ForeignKey('Challenge', on_delete=models.CASCADE, null=True, blank=True,
                                  related_name='challengeaccount', verbose_name='Челлендж')

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
    manager_redist = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                         verbose_name='Менеджер отправил для перераспределения другим')
    sent_to_challenges = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                             verbose_name='Пользователь отправил в фонды челленджей со счёта раздачи')
    sent_to_challenges_from_income = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                                         verbose_name='Пользователь отправил в фонды '
                                                                      'челленджей со счёта получения')
    awarded_from_challenges = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                                  verbose_name='Пользователь получил из фондов в качестве награды')
    returned_from_challenges = models.DecimalField(max_digits=10, decimal_places=0, default=0,
                                                   verbose_name='Пользователь получил из фондов в качестве возврата')

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}

    class Meta:
        db_table = 'user_stats'


class EventObjectTypes(models.TextChoices):
    TRANSACTION = 'T', 'Транзакция'
    QUEST = 'Q', 'Запрос (челлендж, квест)'


class EventRecordTypes(models.TextChoices):
    TRANS_STATUS = 'S', 'Статус транзакции'
    LIKE_ITEM = 'L', 'Лайк'
    COMMENT_ITEM = 'C', 'Комментарий'
    REPORT_ITEM = 'R', 'Отчёт челленджа'


class EventTypes(models.Model):
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


class Event(models.Model):
    class EventObject(models.TextChoices):
        TRANSACTION = 'T', 'Транзакция'
        QUEST = 'Q', 'Челлендж'
        REPORT = 'R', 'Отчёт'
        NEWS = 'N', 'Новости'
        ADVERTISEMENT = 'A', 'Объявление'

    event_type = models.ForeignKey(EventTypes, on_delete=models.PROTECT, verbose_name='Тип события')
    event_object_id = models.IntegerField(null=True, blank=True)
    event_record_id = models.IntegerField(null=True, blank=True)
    object_selector = models.CharField(max_length=1, choices=EventObject.choices, null=True, blank=True,
                                       verbose_name='Селектор объекта')
    time = models.DateTimeField(verbose_name='Время события')
    scope = models.ForeignKey(Organization, on_delete=models.SET_NULL, verbose_name='Область видимости', null=True,
                              blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name='Пользователь', null=True, blank=True)

    class Meta:
        db_table = 'events'

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}


class Comment(models.Model):
    objects = CustomCommentQueryset.as_manager()

    transaction = models.ForeignKey(Transaction, related_name="comments", on_delete=models.SET_NULL,
                                    null=True, blank=True, verbose_name="Транзакция")

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")

    user = models.ForeignKey(User, related_name='comment', on_delete=models.CASCADE,
                             verbose_name='Владелец Комментария')
    date_created = models.DateTimeField(auto_now_add=True, null=True, verbose_name="Дата создания")
    date_last_modified = models.DateTimeField(auto_now=True, null=True, verbose_name="Дата последнего изменения")
    is_last_comment = models.BooleanField(null=True, verbose_name="Последний комментарий в транзакции")
    previous_comment = models.ForeignKey("Comment", null=True, blank=True, related_name='next_comment',
                                         on_delete=models.SET_NULL,
                                         verbose_name='Ссылка на предыдущий комментарий')
    text = models.TextField(default='', blank=True, verbose_name="Текст")
    picture = models.ImageField(blank=True, null=True, upload_to='comments',
                                verbose_name='Картинка Комментария')

    def to_json(self):
        json_dict = {field: getattr(self, field) for field in self.__dict__ if
                     not field.startswith('_') and field != 'picture'}
        if getattr(self, "picture"):
            json_dict['picture'] = self.picture.url
        else:
            json_dict['picture'] = None
        return json_dict

    def __str__(self):
        return self.text

    @property
    def get_picture_url(self):
        if getattr(self, "picture"):
            return self.picture.url

    @property
    def get_thumbnail_photo_url(self):
        if self.picture:
            return f"{get_thumbnail_link(self.picture.url)}"

    class Meta:
        db_table = 'comments'


class LikeKind(models.Model):
    code = models.TextField(verbose_name="Код Типа Лайка", null=True)
    name = models.TextField(verbose_name="Название Типа Лайка")
    icon = models.ImageField(blank=True, null=True, upload_to='icons', verbose_name='Пиктограмма')

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}

    def __str__(self):
        return self.name

    def get_icon_url(self):
        if self.icon:
            return f"{self.icon.url}"
        return None

    class Meta:
        db_table = 'like_kind'


class Like(models.Model):
    objects = CustomLikeQueryset.as_manager()
    transaction = models.ForeignKey(Transaction, null=True, blank=True, related_name="likes", on_delete=models.CASCADE,
                                    verbose_name="Транзакция")

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")

    like_kind = models.ForeignKey(LikeKind, related_name='like', on_delete=models.CASCADE,
                                  verbose_name='Тип лайка')
    is_liked = models.BooleanField(default=False, verbose_name="Выставлен")
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Дата выставления лайка")
    date_deleted = models.DateTimeField(default=None, null=True, blank=True, verbose_name="Дата отзыва лайка")
    user = models.ForeignKey(User, related_name='like', on_delete=models.CASCADE,
                             verbose_name='Владелец Лайка')

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}

    class Meta:
        db_table = 'likes'


class LikeStatistics(models.Model):
    transaction = models.ForeignKey(Transaction, related_name='like_statistics', on_delete=models.SET_NULL,
                                    null=True, blank=True, verbose_name='Транзакция')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")

    like_counter = models.IntegerField(verbose_name='Количество лайков')
    like_kind = models.ForeignKey(LikeKind, related_name='like_statistics', on_delete=models.SET_NULL,
                                  null=True, blank=True, verbose_name='Тип лайка')
    last_change_at = models.DateTimeField(default=None, verbose_name='Время последнего изменения количества лайков',
                                          null=True, blank=True)

    class Meta:
        db_table = 'like_statistics'


class LikeCommentStatistics(models.Model):
    transaction = models.ForeignKey(Transaction, related_name='like_comment_statistics', on_delete=models.SET_NULL,
                                    null=True, blank=True, verbose_name='Транзакция')

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey("content_type", "object_id")

    first_comment = models.ForeignKey("Comment", related_name='first_comment_statistics', on_delete=models.SET_NULL,
                                      null=True, blank=True, verbose_name='Первый комментарий')
    last_comment = models.ForeignKey("Comment", related_name='last_comment_statistics', on_delete=models.SET_NULL,
                                     null=True, blank=True, verbose_name='Последний комментарий')
    last_event_comment = models.ForeignKey("Comment", related_name='last_event_comment_statistics',
                                           blank=True, on_delete=models.SET_NULL, null=True,
                                           verbose_name='Последний добавленный или измененный комментарий')
    last_like_or_comment_change_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Время последнего изменения количества лайков или последнего добавления/изменения комментария',
        null=True, blank=True)
    comment_counter = models.IntegerField(verbose_name='Количество комментариев', default=0)

    class Meta:
        db_table = 'like_comment_statistics'


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

    def to_json_name_only(self):
        return {field: getattr(self, field) for field in self.__dict__
                if not field.startswith('_') and field in ('id', 'name')}

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
    tagged_object = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='_objecttags',
                                      verbose_name='Объект')
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


class ChallengeState(models.TextChoices):
    PUBLISHED = 'P', 'Опубликован'
    REGISTRATION = 'R', 'Идёт регистрация'
    GET_REPORTS = 'G', 'Идёт приём отчётов'
    FINALIZING = 'F', 'Подводятся итоги'
    COMPLETED = 'C', 'Завершен'


class ChallengeMode(models.TextChoices):
    FROM_ORGANIZATION = 'O', 'От имени организации'
    FROM_USER = 'U', 'От имени пользователя'
    IS_PUBLIC = 'P', 'Является публичным'
    IS_TEAM = 'C', 'Является командным'
    WITH_REGISTER = 'R', 'Нужна регистрация'
    WITH_IMAGE = 'G', 'Нужна картинка'
    NO_COMMENTS = 'M', 'Запрет комментариев'
    ONLY_PARTICIPANTS_COMMENTS = 'E', 'Разрешить комментарии только для участников'
    NO_LIKES = 'L', 'Лайки запрещены'
    ONLY_PARTICIPANTS_LIKES = 'T', 'Разрешить лайки только для участников'
    REPORTS_COMMENTS_EXCEPT_GROUPS = 'X', 'Комментарии отчетов разрешены только автору отчета, организатору и судьям'
    REPORTS_COMMENTS_PARTICIPANTS_ONLY = 'W', 'Комментарии отчетов разрешены только участникам'
    REPORTS_LIKES_PARTICIPANTS_ONLY = 'I', 'Лайки отчетов разрешены только участникам'
    CAN_USE_NICKNAME = 'N', 'Участник может использовать никнейм'
    CAN_MAKE_PRIVATE = 'H', 'Участник может сделать отчёт приватным'
    ANONYMOUS_MODE = 'A', 'Отчеты анонимизированы до подведения итогов, не видны ни имена пользователей, ни псевдонимы'
    CAN_SEND_INVITES = 'Q', 'Участник может рассылать приглашения'
    CONFIRMATION_RULE = 'Y', 'Подтверждение будет выполняться судейской коллегией (через выдачу ими баллов)'
    ONE_REPORT_MAX = 'K', 'Максимум 1 отчет для отправки для каждого участника'


class ChallengeParticipants(models.TextChoices):
    NOT_A_PARTICIPANT = 'X', 'Сторонний наблюдатель'
    INVITED = 'I', 'Приглашённый участник'
    REGISTERED = 'R', 'Записавшийся участник'
    SEND_REPORT = 'S', 'Участник, приславший отчет о выполнении задания'
    CONFIRM_REPORT = 'C', 'Участник, отчет которого подтвержден'
    HAS_REWARD = 'M', 'Участник, которому назначено вознаграждение'
    JUDGE = 'J', 'Член судейской комиссии'
    HEAD = 'H', 'Руководители подразделения или организации, на уровне которой объявлен челлендж'


class Challenge(models.Model):
    objects = CustomChallengeQueryset.as_manager()

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challengecreators',
                                verbose_name='Создатель')
    organized_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challengeorganizers',
                                     verbose_name='Организатор')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='Время публикации в ленте')
    registration_start_at = models.DateTimeField(null=True, blank=True,
                                                 verbose_name='Время начала регистрации участников')
    registration_end_at = models.DateTimeField(null=True, blank=True,
                                               verbose_name='Время окончания регистрации участников')
    reports_start_at = models.DateTimeField(null=True, blank=True,
                                            verbose_name='Время начала приема отчетов о выполнении задания участниками')
    reports_end_at = models.DateTimeField(null=True, blank=True,
                                          verbose_name='Время завершения приема отчетов о '
                                                       'выполнении задания участниками')
    end_at = models.DateTimeField(null=True, blank=True, verbose_name='Время завершения вызова')
    states = ArrayField(models.CharField(max_length=1, choices=ChallengeState.choices), size=5)
    to_hold = models.ForeignKey(Organization, related_name='challengestohold', on_delete=models.CASCADE,
                                null=True, blank=True,
                                verbose_name='Организация, от имени которой проводится вызов')
    to_level_publicity = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True,
                                           related_name='challengestopublic',
                                           verbose_name='Организация, определяющая уровень публичности'
                                                        ' вызова')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='challengeorganizations',
                                     verbose_name='Организация, где проходит челлендж')
    name = CICharField(max_length=200, verbose_name='Название вызова')
    description = CITextField(default='', blank=True, verbose_name='Описание вызова')
    photo = models.ImageField(null=True, blank=True, upload_to='challenges', verbose_name='Эмблема')
    min_contribution = models.PositiveIntegerField(null=True, blank=True, default=0,
                                                   verbose_name='')
    max_contribution = models.PositiveIntegerField(null=True, blank=True, default=0,
                                                   verbose_name='')
    challenge_mode = ArrayField(models.CharField(max_length=1, choices=ChallengeMode.choices),
                                size=20, null=True, blank=True)
    parameters = models.JSONField(verbose_name='Параметры алгоритма', null=True, blank=True)
    distribution_type = CICharField(max_length=100, verbose_name='Тип распределения вознаграждений',
                                    null=True, blank=True)
    return_period = models.CharField(max_length=50,
                                     verbose_name='Период для отзыва подтверждений выполнения заданий и вознаграждений',
                                     null=True, blank=True)
    start_balance = models.PositiveIntegerField(verbose_name='Начальный объём фонда от организатора')
    full_incomes = models.PositiveIntegerField(null=True, blank=True,
                                               verbose_name='Общий объем поступлений фонда')
    full_distributions = models.PositiveIntegerField(null=True, blank=True,
                                                     verbose_name='Общий объем выданных из фонда вознаграждений')
    next_reward_size = models.PositiveIntegerField(null=True, blank=True,
                                                   verbose_name='Размер очередного вознаграждения')
    list_visibility = models.JSONField(null=True, blank=True, verbose_name='Видимость списков')
    participants_count = models.PositiveIntegerField(default=0, verbose_name='Текущее количество участников')
    winners_count = models.PositiveIntegerField(default=0, verbose_name='Текущее количество победителей')

    class Meta:
        db_table = 'challenges'

    def __str__(self):
        return self.name

    @property
    def get_photo_url(self):
        if self.photo:
            return self.photo.url

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}


class ParticipantModes(models.TextChoices):
    IS_RELEVANT = 'A', 'Запись актуальна'
    INVITE = 'Q', 'Приглашение'
    ACCEPT = 'P', 'Пользователь подтвердил участие'
    HIDDEN = 'H', 'Скрыть связь с пользователем'
    JUDGE = 'R', 'Судья'
    ORGANIZER = 'O', 'Организатор'
    WINNER = 'W', 'Победитель'


class ChallengeParticipant(models.Model):
    objects = CustomChallengeParticipantQueryset.as_manager()

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время создания записи')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Время обновления записи')
    register_time = models.DateTimeField(null=True, blank=True, verbose_name='Время регистрации')
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='participants',
                                  verbose_name='Челлендж')
    user_participant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challengeuserparticipants',
                                         verbose_name='Пользователь-участник')
    team_participant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challengeteamparticipants',
                                         verbose_name='Команда-участник', null=True, blank=True)
    invite_from = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challengeinvitors',
                                    verbose_name='Команда-участник', null=True, blank=True)
    nickname = CICharField(max_length=100, verbose_name='Никнейм', null=True, blank=True)
    contribution = models.PositiveIntegerField(verbose_name='Взнос участника')
    points_received = models.PositiveIntegerField(null=True, blank=True,
                                                  verbose_name='Количество присужденных баллов')
    place = models.PositiveIntegerField(null=True, blank=True, verbose_name='Место в списке победителей')
    total_received = models.PositiveIntegerField(default=0, verbose_name='Сумма полученного выигрыша или возврата')
    mode = ArrayField(models.CharField(max_length=1, choices=ParticipantModes.choices), size=6)

    class Meta:
        db_table = 'challenge_participants'


class ReportTypes(models.TextChoices):
    SENT_TO_APPROVE = 'S', 'Направлен организатору для подтверждения'
    IN_PROCESS = 'F', 'В процессе оценки судьями'
    APPROVED = 'A', 'Подтверждено'
    DECLINED = 'D', 'Отклонено'
    DOUBLE_CHECK = 'R', 'Повторно направлено организатору'
    REWARD_RECEIVED = 'W', 'Получено вознаграждение'


class ChallengeReport(models.Model):
    objects = CustomChallengeReportQueryset.as_manager()

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Время обновления')
    content_updated_at = models.DateTimeField(auto_now=True,
                                              verbose_name='Время последнего обновления текста или картинки')
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='reports',
                                  verbose_name='Челлендж')
    participant = models.ForeignKey(ChallengeParticipant, on_delete=models.CASCADE, related_name='challengereports',
                                    verbose_name='Запись участника')
    text = models.TextField(default='', blank=True, verbose_name='Текст')
    photo = models.ImageField(null=True, blank=True, upload_to='reports', verbose_name='Картинка/скриншот')
    points = models.PositiveIntegerField(null=True, blank=True, verbose_name='Количество присуждённых баллов')
    state = models.CharField(max_length=1, choices=ReportTypes.choices, verbose_name='Состояние отчёта')
    is_public = models.BooleanField(default=True, verbose_name='Публичность')

    class Meta:
        db_table = 'challenge_reports'

    @property
    def get_photo_url(self):
        if self.photo:
            return self.photo.url


class FCMToken(models.Model):
    token = models.CharField(max_length=255, verbose_name='Токен', db_index=True)
    device = models.CharField(max_length=255, verbose_name='Устройство', default='')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь', related_name='fcmtokens')

    class Meta:
        db_table = 'fcm_tokens'

    def __str__(self):
        return self.token


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        LIKE = 'L', 'Лайк'
        COMMENT = 'C', 'Комментарий'
        CHALLENGE = 'H', 'Челлендж'
        TRANSACTION = 'T', 'Перевод'
        CHALLENGE_WIN = 'W', 'Победа в челлендже'
        REPORT = 'R', 'Отправлен отчёт'

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь', related_name='notifications')
    from_user = models.PositiveIntegerField(null=True, blank=True, verbose_name='Инициировавший событие пользователь')
    type = models.CharField(max_length=1, choices=NotificationType.choices, verbose_name='Тип уведомления')
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='Идентификатор связанного объекта')
    data = models.JSONField(null=True, blank=True, verbose_name='Данные, переданные с уведомлением')
    theme = models.CharField(max_length=255, verbose_name='Тема')
    text = models.TextField(verbose_name='Текст')
    read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Изменено')

    class Meta:
        db_table = 'notifications'

    def to_json(self):
        return {field: getattr(self, field) for field in self.__dict__ if not field.startswith('_')}


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
            amount=0,
            organization_id=instance.organization_id
        )


@receiver(post_save, sender=Profile)
def create_frozen_account(instance: Profile, created: bool, **kwargs):
    if created:
        Account.objects.create(
            owner=instance.user,
            account_type='F',
            amount=0,
            organization_id=instance.organization_id
        )


@receiver(post_save, sender=Profile)
def create_frozen_account(instance: Profile, created: bool, **kwargs):
    if created:
        Account.objects.create(
            owner=instance.user,
            account_type='D',
            amount=0,
            organization_id=instance.organization_id
        )


@receiver(post_save, sender=Profile)
def create_user_stat(instance: Profile, created: bool, **kwargs):
    if created:
        from utils.current_period import get_current_period
        period = get_current_period(instance.organization_id)
        if period:
            UserStat.objects.create(
                user=instance.user,
                period=period
            )
