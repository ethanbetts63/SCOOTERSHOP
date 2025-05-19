# hire/views/step6_PaymentDetails_view.py
from django.shortcuts import render
from django.views import View

class PaymentDetailsView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'hire/step6_payment_details.html', {})