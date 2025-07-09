from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin

from .models.PaymentModel import Payment
from .models.RefundPolicySettings import RefundPolicySettings
from .models.RefundRequest import RefundRequest
from .models.WebhookEvent import WebhookEvent

# --- Resource Classes for Import/Export ---

class PaymentResource(resources.ModelResource):
    class Meta:
        model = Payment
        import_id_fields = ('stripe_payment_intent_id',)
        fields = (
            'id', 'stripe_payment_intent_id', 'amount', 'currency', 'status',
            'payment_method_type', 'created_at', 'service_booking', 'sales_booking'
        )
        export_order = fields

class RefundRequestResource(resources.ModelResource):
    payment = fields.Field(widget=ForeignKeyWidget(Payment, 'stripe_payment_intent_id'))

    class Meta:
        model = RefundRequest
        # FIX: Removed 'resolved_at' as it does not exist on the model
        fields = ('id', 'payment', 'reason', 'status', 'requested_at',)
        export_order = fields


# --- Updated ModelAdmin Classes ---

@admin.register(Payment)
class PaymentAdmin(ImportExportModelAdmin):
    resource_class = PaymentResource
    list_display = ('stripe_payment_intent_id', 'amount', 'status', 'created_at', 'service_booking', 'sales_booking')
    # FIX: Removed 'payment_method_type' as it cannot be used as a filter
    list_filter = ('status', 'created_at')
    search_fields = ('stripe_payment_intent_id', 'service_booking__service_booking_reference', 'sales_booking__sales_booking_reference')
    raw_id_fields = ('service_booking', 'sales_booking')

@admin.register(RefundRequest)
class RefundRequestAdmin(ImportExportModelAdmin):
    resource_class = RefundRequestResource
    # FIX: Removed 'resolved_at' from list_display
    list_display = ('payment', 'status', 'requested_at')
    list_filter = ('status',)
    search_fields = ('payment__stripe_payment_intent_id',)
    raw_id_fields = ('payment',)


# --- Unchanged Admin Classes ---

@admin.register(RefundPolicySettings)
class RefundPolicySettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not RefundPolicySettings.objects.exists()

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    # FIX: Removed 'status' and 'error_message' as they do not exist on the model
    list_display = ('event_type', 'received_at')
    # FIX: Removed 'status' from list_filter
    list_filter = ('event_type',)
    search_fields = ('event_id',)

