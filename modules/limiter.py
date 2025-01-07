from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import config

limiter = Limiter(key_func=get_remote_address)

def init_limiter(app):
    limiter.init_app(app)
    limiter.storage_uri = config.MONGO_STRING
    limiter.default_limits = [
        f"{config.AUTH_LIMITER_PER_DAY} per day",
        f"{config.AUTH_LIMITER_PER_HOUR} per hour",
    ]
    limiter.strategy = "fixed-window"