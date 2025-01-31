import logging
import logging.handlers


HOST = '127.0.0.1'
PORT = logging.handlers.DEFAULT_TCP_LOGGING_PORT


def get_socket_handler():
    s_handler = logging.handlers.SocketHandler(HOST, PORT)
    return s_handler


def get_logger(name=None):
    logger = logging.getLogger(name)
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.DEBUG)
    return logger
