                                                                          

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.contrib import messages
from inventory.mixins import AdminRequiredMixin
from inventory.forms import AdminSalesFAQForm
from inventory.models import SalesFAQ

class SalesFAQCreateUpdateView(AdminRequiredMixin, View):
    """
    View to handle creating and updating Sales FAQs.
    """
    template_name = 'inventory/admin_sales_faq_create_update.html'
    form_class = AdminSalesFAQForm

    def get(self, request, pk=None, *args, **kwargs):
        """
        Handles GET requests to display the form for creating or editing an FAQ.
        """
        if pk:
            instance = get_object_or_404(SalesFAQ, pk=pk)
            form = self.form_class(instance=instance)
        else:
            instance = None
            form = self.form_class()

        context = {
            'form': form,
            'is_edit_mode': bool(pk),
            'page_title': "Edit Sales FAQ" if pk else "Create Sales FAQ"
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        """
        Handles POST requests to save the form data.
        """
        if pk:
            instance = get_object_or_404(SalesFAQ, pk=pk)
            form = self.form_class(request.POST, instance=instance)
        else:
            instance = None
            form = self.form_class(request.POST)

        if form.is_valid():
            faq = form.save()
            if pk:
                messages.success(request, f"Sales FAQ '{faq.question[:50]}...' updated successfully.")
            else:
                messages.success(request, f"Sales FAQ '{faq.question[:50]}...' created successfully.")
            return redirect(reverse('inventory:sales_faq_management'))
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,
                'is_edit_mode': bool(pk),
                'page_title': "Edit Sales FAQ" if pk else "Create Sales FAQ"
            }
            return render(request, self.template_name, context)

