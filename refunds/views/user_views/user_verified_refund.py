from django.shortcuts import render
from django.views import View


class UserVerifiedRefundView(View):
    template_name = "refunds/user_verified_refund.html"

    def get(self, request, *args, **kwargs):
        context = {
            "page_title": "Refund Request Verified",
            "message": "Your refund request has been successfully verified!",
            "additional_info": "It will now be reviewed by our administration team as soon as possible. You will receive another email once your request has been processed.",
        }
        return render(request, self.template_name, context)
