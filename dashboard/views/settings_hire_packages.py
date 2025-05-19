from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from hire.models.hire_packages import Package # Make sure this import path is correct

@method_decorator(login_required, name='dispatch')
class HirePackagesSettingsView(View):
    template_name = 'dashboard/settings_hire_packages.html'

    def get(self, request, *args, **kwargs):
        packages = Package.objects.all().order_by('name')
        context = {
            'packages': packages
        }
        return render(request, self.template_name, context)