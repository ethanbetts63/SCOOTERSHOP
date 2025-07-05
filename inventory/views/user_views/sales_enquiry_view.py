from django.shortcuts import render, redirect
from django.views import View
from inventory.forms.sales_enquiry_form import SalesEnquiryForm
from inventory.models.motorcycle import Motorcycle

class SalesEnquiryView(View):
    def get(self, request, motorcycle_id):
        motorcycle = Motorcycle.objects.get(id=motorcycle_id)
        form = SalesEnquiryForm(initial={'motorcycle': motorcycle})
        return render(request, 'inventory/sales_enquiry.html', {'form': form, 'motorcycle': motorcycle})

    def post(self, request, motorcycle_id):
        motorcycle = Motorcycle.objects.get(id=motorcycle_id)
        form = SalesEnquiryForm(request.POST)
        if form.is_valid():
            form.save()
            # Redirect to a success page or back to the motorcycle detail page
            return redirect('inventory:motorcycle-detail', pk=motorcycle_id)
        return render(request, 'inventory/sales_enquiry.html', {'form': form, 'motorcycle': motorcycle})
