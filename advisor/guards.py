from functools import wraps
from django.http import JsonResponse
from django.utils import timezone
from .models import AdvisorAccess

def require_advisor_access(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "AUTH_REQUIRED"}, status=401)

        ok = AdvisorAccess.objects.filter(
            user=request.user,
            active_until__gt=timezone.now()
        ).exists()

        if not ok:
            return JsonResponse({"error": "PAYMENT_REQUIRED", "pay_url": "/advisor/pay/"}, status=402)

        return view_func(request, *args, **kwargs)
    return _wrapped
