from slowapi import Limiter
from slowapi.util import get_remote_address

# Default limiter using in-memory storage (can be configured for Redis in production)
limiter = Limiter(key_func=get_remote_address)
