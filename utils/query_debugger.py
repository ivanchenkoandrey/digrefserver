from functools import wraps
import logging
import time

from django.db import connection, reset_queries

logger = logging.getLogger(__name__)


def query_debugger(func):
    @wraps(func)
    def inner_func(*args, **kwargs):
        reset_queries()
        start_queries = len(connection.queries)
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        end_queries = len(connection.queries)

        logger.info(f"Метод : {func.__qualname__}")
        logger.info(f"{connection.queries=}")
        logger.info(f"Количество запросов : {end_queries - start_queries}")
        logger.info(f"Получено за {(end - start):.2f} секунд")
        return result
    return inner_func
