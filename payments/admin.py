from django.contrib import admin
from .models.PaymentModel import Payment
from .models.RefundPolicySettings import RefundPolicySettings
from .models.RefundRequest import RefundRequest
from .models.WebhookEvent import WebhookEvent

admin.site.register(Payment)
admin.site.register(RefundPolicySettings)
admin.site.register(RefundRequest)
admin.site.register(WebhookEvent)
