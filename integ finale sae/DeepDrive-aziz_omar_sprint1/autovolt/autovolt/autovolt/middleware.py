from django.shortcuts import redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied

class BackOfficeAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""
        if path.startswith("/back/"):
            if not request.user.is_authenticated:
                return redirect(f"{reverse('login')}?next={request.get_full_path()}")
            if not (request.user.is_staff and getattr(request.user, "role", "") == "admin"):
                raise PermissionDenied  
        return self.get_response(request)