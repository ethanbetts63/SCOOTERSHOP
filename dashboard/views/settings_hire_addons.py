                                         

from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from hire.models import AddOn                         

class SettingsHireAddOnsView(LoginRequiredMixin, View):
    template_name = 'dashboard/settings_hire_addons.html'

    def get(self, request):
        addons = AddOn.objects.all().order_by('name')                                
        context = {
            'addons': addons,
            'total_addons': addons.count(),
        }
        return render(request, self.template_name, context)

                                                       
settings_hire_addons = SettingsHireAddOnsView.as_view()