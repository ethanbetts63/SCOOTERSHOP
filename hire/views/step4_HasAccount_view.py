from django.shortcuts import render

def step4_has_account_view(request):
    return render(request, 'hire/step4_has_account.html', {})