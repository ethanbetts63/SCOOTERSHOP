# hire/views/step4_HasAccount_view.py
from django.shortcuts import render
from django.views import View

class HasAccountView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'hire/step4_has_account.html', {})