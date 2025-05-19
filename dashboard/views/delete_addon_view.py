# dashboard/views/delete_addon_view.py

from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from hire.models import AddOn

@login_required
@require_POST
def delete_addon(request, pk):
    """
    Deletes an AddOn instance.
    """
    addon = get_object_or_404(AddOn, pk=pk)
    try:
        addon.delete()
        messages.success(request, f"Add-On '{addon.name}' deleted successfully.")
    except IntegrityError:
        messages.error(request, f"Cannot delete add-on '{addon.name}' because it is associated with existing bookings or packages. Please set it as unavailable instead.")
    except Exception as e:
        messages.error(request, f"An error occurred while deleting add-on '{addon.name}': {e}")

    return redirect('dashboard:settings_hire_addons')