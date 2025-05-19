# dashboard/views/settings_hire_addons.py

from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from hire.models import AddOn # Import the AddOn model

class SettingsHireAddOnsView(LoginRequiredMixin, View):
    template_name = 'dashboard/settings_hire_addons.html'

    def get(self, request):
        addons = AddOn.objects.all().order_by('name') # Order by name for consistency
        context = {
            'addons': addons,
            'total_addons': addons.count(),
        }
        return render(request, self.template_name, context)

# Alias for consistent naming with other settings views
settings_hire_addons = SettingsHireAddOnsView.as_view()