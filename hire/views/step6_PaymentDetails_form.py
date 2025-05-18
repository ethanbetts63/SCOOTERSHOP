from django.shortcuts import render

def step6_payment_details_view(request):
    return render(request, 'hire/step6_payment_details.html', {})