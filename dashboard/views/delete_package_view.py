from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db.models import ProtectedError                        
from hire.models.hire_packages import Package                                        

@method_decorator(login_required, name='dispatch')
class DeletePackageView(View):
    def post(self, request, pk, *args, **kwargs):
        package = get_object_or_404(Package, pk=pk)
        package_name = package.name
        try:
            package.delete()
            messages.success(request, f"Package '{package_name}' deleted successfully!")
        except ProtectedError:
            messages.error(request, f"Cannot delete package '{package_name}' because it is associated with existing bookings.")
        except Exception as e:
            messages.error(request, f"An error occurred while deleting package '{package_name}': {e}")
        return redirect('dashboard:settings_hire_packages')