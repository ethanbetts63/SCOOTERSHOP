from django.contrib import admin
from .models import RefundTerms


@admin.register(RefundTerms)
class RefundTermsAdmin(admin.ModelAdmin):
    list_display = ("version_number", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("content",)
    ordering = ("-version_number",)

    fieldsets = (
        (None, {"fields": ("is_active", "content")}),
        (
            "Deposit Refund Settings",
            {
                "fields": (
                    "deposit_full_refund_days",
                    "deposit_partial_refund_days",
                    "deposit_partial_refund_percentage",
                    "deposit_no_refund_days",
                )
            },
        ),
        (
            "Full Payment Refund Settings",
            {
                "fields": (
                    "full_payment_full_refund_days",
                    "full_payment_partial_refund_days",
                    "full_payment_partial_refund_percentage",
                    "full_payment_no_refund_days",
                )
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ("version_number",)
        return self.readonly_fields
