from rest_framework.exceptions import ValidationError


def process_offset_and_limit(offset, limit):
    if offset is None and limit is None:
        return 0, 20
    if offset == '' and limit == '':
        return 0, 20
    if offset is None and limit is not None:
        raise ValidationError('Передайте offset')
    if limit is None and offset is not None:
        raise ValidationError('Передайте limit')
    try:
        offset, limit = list(map(int, (offset, limit)))
        return offset - 1 if offset > 0 else 0, limit
    except ValueError:
        raise ValidationError('Передайте числами параметры offset и limit')
