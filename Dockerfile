FROM python:3.8-alpine
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache --virtual .tmp-build-deps \
    gcc libc-dev linux-headers postgresql-dev \
    && apk add libffi-dev
WORKDIR /usr/bin/tfapp
COPY requirements.txt /usr/bin/tfapp
RUN pip install -r requirements.txt --upgrade pip
COPY . .
CMD ["gunicorn", "--bind", ":8888", "--workers", "4", "digrefserver.wsgi:application"]