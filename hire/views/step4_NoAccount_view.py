from django.shortcuts import render

def step4_no_account_view(request):
    return render(request, 'hire/step4_no_account.html', {})