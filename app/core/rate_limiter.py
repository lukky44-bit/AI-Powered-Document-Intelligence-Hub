from slowapi import Limiter
from slowapi.util import get_remote_address


def user_key_func(request):
    user = getattr(request.state, "user", None)
    if user and "email" in user:
        return user["email"]
    return get_remote_address(request)


limiter = Limiter(key_func=user_key_func)
