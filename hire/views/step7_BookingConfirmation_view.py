# hire/views/step7_BookingConfirmation_view.py
from django.shortcuts import render
from django.views import View

class BookingConfirmationView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'hire/step7_booking_confirmation.html', {})