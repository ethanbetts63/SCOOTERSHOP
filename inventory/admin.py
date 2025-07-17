from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin

from .models import (
    BlockedSalesDate,
    FeaturedMotorcycle,
    InventorySettings,
    Motorcycle,
    MotorcycleCondition,
    MotorcycleImage,
    SalesBooking,
    Salesfaq,
    SalesProfile,
    SalesTerms,
    TempSalesBooking,
)

# --- Resource Classes for Import/Export ---


class MotorcycleConditionResource(resources.ModelResource):
    class Meta:
        model = MotorcycleCondition
        fields = (
            "id",
            "name",
        )


class SalesProfileResource(resources.ModelResource):
    class Meta:
        model = SalesProfile
        import_id_fields = ("email",)
        fields = (
            "id",
            "name",
            "email",
            "phone_number",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "post_code",
            "country",
        )
        export_order = fields


class MotorcycleResource(resources.ModelResource):
    condition = fields.Field(widget=ForeignKeyWidget(MotorcycleCondition, "name"))

    class Meta:
        model = Motorcycle
        import_id_fields = ("stock_number",)
        # FIX: Removed 'is_sold' as it does not exist on the model
        fields = (
            "id",
            "stock_number",
            "vin_number",
            "brand",
            "model",
            "year",
            "price",
            "condition",
            "status",
            "meta_title",
        )
        export_order = fields


class SalesBookingResource(resources.ModelResource):
    sales_profile = fields.Field(widget=ForeignKeyWidget(SalesProfile, "email"))
    motorcycle = fields.Field(widget=ForeignKeyWidget(Motorcycle, "stock_number"))

    class Meta:
        model = SalesBooking
        import_id_fields = ("sales_booking_reference",)
        fields = (
            "id",
            "sales_booking_reference",
            "sales_profile",
            "motorcycle",
            "booking_status",
            "payment_status",
            "payment_method",
            "customer_notes",
            "calculated_total",
            "amount_paid",
        )
        export_order = fields


# --- Inline Admin for Motorcycle Images ---


class MotorcycleImageInline(admin.TabularInline):
    model = MotorcycleImage
    extra = 1
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        from django.utils.html import format_html

        if obj.image:
            return format_html(
                '<img src="{}" width="150" height="auto" />', obj.image.url
            )
        return "(No image)"

    image_preview.short_description = "Image Preview"


# --- Updated ModelAdmin Classes ---


@admin.register(Motorcycle)
class MotorcycleAdmin(ImportExportModelAdmin):
    resource_class = MotorcycleResource
    inlines = [MotorcycleImageInline]
    # FIX: Removed 'is_sold' from list_display
    list_display = (
        "stock_number",
        "brand",
        "model",
        "year",
        "price",
        "condition",
        "status",
    )
    # FIX: Removed 'is_sold' from list_filter
    list_filter = ("brand", "condition", "status", "year")
    search_fields = ("stock_number", "vin_number", "brand", "model")


@admin.register(SalesBooking)
class SalesBookingAdmin(ImportExportModelAdmin):
    resource_class = SalesBookingResource
    list_display = (
        "sales_booking_reference",
        "motorcycle",
        "sales_profile",
        "booking_status",
        "payment_status",
    )
    list_filter = ("booking_status", "payment_status")
    search_fields = (
        "sales_booking_reference",
        "sales_profile__name",
        "sales_profile__email",
        "motorcycle__stock_number",
    )
    raw_id_fields = ("sales_profile", "motorcycle", "payment")


@admin.register(SalesProfile)
class SalesProfileAdmin(ImportExportModelAdmin):
    resource_class = SalesProfileResource
    list_display = ("name", "email", "phone_number", "city")
    search_fields = ("name", "email", "phone_number")


@admin.register(MotorcycleCondition)
class MotorcycleConditionAdmin(ImportExportModelAdmin):
    resource_class = MotorcycleConditionResource
    list_display = ("name",)
    search_fields = ("name",)


# --- Unchanged Admin Classes ---

admin.site.register(BlockedSalesDate)
admin.site.register(FeaturedMotorcycle)
admin.site.register(InventorySettings)
admin.site.register(Salesfaq)
admin.site.register(SalesTerms)
admin.site.register(TempSalesBooking)
