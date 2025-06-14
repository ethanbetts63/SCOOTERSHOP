# SCOOTER_SHOP/inventory/views/admin_views/sales_profile_create_update_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from inventory.forms import AdminSalesProfileForm # Assuming you'll create inventory/forms/__init__.py
from inventory.models import SalesProfile


class SalesProfileCreateUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'inventory/admin_sales_profile_create_update.html'
    form_class = AdminSalesProfileForm

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, pk=None, *args, **kwargs):
        instance = None
        if pk:
            instance = get_object_or_404(SalesProfile, pk=pk)
            form = self.form_class(instance=instance)
        else:
            form = self.form_class()

        context = {
            'form': form,
            'is_edit_mode': bool(pk),
            'current_profile': instance,
            'page_title': "Edit Sales Profile" if pk else "Create Sales Profile"
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        instance = None
        if pk:
            instance = get_object_or_404(SalesProfile, pk=pk)
            form = self.form_class(request.POST, request.FILES, instance=instance)
        else:
            form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            sales_profile = form.save()
            if pk:
                messages.success(request, f"Sales Profile for '{sales_profile.name}' updated successfully.")
            else:
                messages.success(request, f"Sales Profile for '{sales_profile.name}' created successfully.")
            return redirect(reverse('inventory:sales_profile_management'))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,
                'is_edit_mode': bool(pk),
                'current_profile': instance,
                'page_title': "Edit Sales Profile" if pk else "Create Sales Profile"
            }
            return render(request, self.template_name, context)

