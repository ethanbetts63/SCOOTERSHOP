from functools import wraps
from django.http import JsonResponse

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"status": "error", "message": "Authentication required."}, status=401
            )
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse(
                {"status": "error", "message": "Admin access required."}, status=403
            )
        return view_func(request, *args, **kwargs)

    return _wrapped_view
