# chat/middleware.py

from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings


class SingleSessionMiddleware:
    """
    Tracks the active session. The blocking logic now lives in the login views.
    This middleware just ensures that if the stored session key changes,
    the current session is still valid (it shouldn't generally happen with blocking,
    but it's good hygiene to keep the session aligned with the profile).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
                stored_key = profile.session_key
                current_key = request.session.session_key

                # If for some anomalous reason the session keys don't match,
                # we don't automatically log out anymore because we actively BLOCK
                # concurrent logins. But if the stored key is empty, we sync it.
                if current_key and not stored_key:
                    profile.session_key = current_key
                    profile.save(update_fields=['session_key'])

            except Exception:
                pass

        return self.get_response(request)
