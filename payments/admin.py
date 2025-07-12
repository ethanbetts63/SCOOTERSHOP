from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models.PaymentModel import Payment
from .models.WebhookEvent import WebhookEvent

class PaymentResource(resources.ModelResource):
    class Meta:
        model = Payment
        import_id_fields = ('stripe_payment_intent_id',)
        fields = (
            'id', 'stripe_payment_intent_id', 'amount', 'currency', 'status',
            'payment_method_type', 'created_at', 'service_booking', 'sales_booking'
        )
        export_order = fields

@admin.register(Payment)
class PaymentAdmin(ImportExportModelAdmin):
    resource_class = PaymentResource
    list_display = ('stripe_payment_intent_id', 'amount', 'status', 'created_at', 'service_booking', 'sales_booking')
    list_filter = ('status', 'created_at')
    search_fields = ('stripe_payment_intent_id', 'service_booking__service_booking_reference', 'sales_booking__sales_booking_reference')
    raw_id_fields = ('service_booking', 'sales_booking')

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'received_at')
    list_filter = ('event_type',)
    search_fields = ('event_id',)

