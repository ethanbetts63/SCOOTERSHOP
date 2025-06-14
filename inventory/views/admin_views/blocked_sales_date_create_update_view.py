# SCOOTER_SHOP/inventory/views/admin_views/blocked_sales_date_create_update_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from inventory.forms import AdminBlockedSalesDateForm # Ensure this import path is correct
from inventory.models import BlockedSalesDate

class BlockedSalesDateCreateUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'inventory/admin_blocked_sales_date_create_update.html'
    form_class = AdminBlockedSalesDateForm

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, pk=None, *args, **kwargs):
        instance = None
        if pk:
            instance = get_object_or_404(BlockedSalesDate, pk=pk)
            form = self.form_class(instance=instance)
        else:
            form = self.form_class()

        context = {
            'form': form,
            'is_edit_mode': bool(pk),
            'current_blocked_date': instance,
            'page_title': "Edit Blocked Sales Date" if pk else "Create New Blocked Sales Date"
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        instance = None
        if pk:
            instance = get_object_or_404(BlockedSalesDate, pk=pk)
            form = self.form_class(request.POST, instance=instance)
        else:
            form = self.form_class(request.POST)

        if form.is_valid():
            blocked_date = form.save()
            if pk:
                messages.success(request, f"Blocked sales date '{blocked_date}' updated successfully.")
            else:
                messages.success(request, f"Blocked sales date '{blocked_date}' created successfully.")
            return redirect(reverse('inventory:blocked_sales_date_management'))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,
                'is_edit_mode': bool(pk),
                'current_blocked_date': instance,
                'page_title': "Edit Blocked Sales Date" if pk else "Create New Blocked Sales Date"
            }
            return render(request, self.template_name, context)

