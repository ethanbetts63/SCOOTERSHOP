# hire/views/step5_BookSumAndPaymentOptions_view.py
from django.shortcuts import render
from django.views import View

class BookSumAndPaymentOptionsView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'hire/step5_book_sum_and_payment_options.html', {})