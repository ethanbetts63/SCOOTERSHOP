from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from service.models import ServiceType


class ServiceTypeManagementView(LoginRequiredMixin, UserPassesTestMixin, View):

    template_name = "service/admin_service_type_management.html"

    def test_func(self):

        return self.request.user.is_staff or self.request.user.is_superuser

    def get_service_types_for_display(self):

        return ServiceType.objects.all().order_by("name")

    def get(self, request, *args, **kwargs):

        service_types = self.get_service_types_for_display()

        context = {
            "service_types": service_types,
        }
        return render(request, self.template_name, context)
