# pylint: disable=C0111,C0103,W0511,W1201
import logging


# TODO: More logic around boto handling errors etc
def exception_handler(errors=(Exception,)):
    def decorator(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except errors as e:
                logging.exception("%s" % (e))
                raise
        return wrapper
    return decorator
