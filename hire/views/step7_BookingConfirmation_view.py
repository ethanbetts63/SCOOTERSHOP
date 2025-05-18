from django.shortcuts import render

def step7_booking_confirmation_view(request):
    return render(request, 'hire/step7_booking_confirmation.html', {})