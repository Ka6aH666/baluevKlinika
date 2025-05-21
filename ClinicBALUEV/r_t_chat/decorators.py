# decorators.py
# Path: appointment/decorators.py

"""
Author: Adams Pierre David
Since: 2.0.0
"""

from functools import wraps

from django.http import JsonResponse


def require_superuser(func):
    """Decorator to require a user to be a superuser.
    Usage: @require_superuser
    """

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            return JsonResponse(
                "Not authorized.",
                status=403,
                success=False,
            )
        return func(request, *args, **kwargs)

    return wrapper
