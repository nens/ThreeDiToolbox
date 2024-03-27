from contextlib import contextmanager
from time import time
import logging

logger = logging.getLogger(__name__)


@contextmanager
def timing(message):
    start = time()
    yield
    stop = time()
    milliseconds = round(1000 * (stop - start))
    logger.info(f'{message}: {milliseconds} ms')
