from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin

from service.models import (
    ServiceType,
    CustomerMotorcycle,
    ServiceBooking,
    ServiceProfile,
    ServiceBrand,
    ServiceSettings,
    BlockedServiceDate,
    TempServiceBooking,
    Servicefaq,
    ServiceTerms,
)

# --- Resource Classes for Import/Export ---
# These classes define how models are mapped to import/export formats.


class ServiceTypeResource(resources.ModelResource):
    class Meta:
        model = ServiceType
        fields = (
            "id",
            "name",
            "base_price",
            "estimated_duration",
            "is_active",
        )
        export_order = fields


class ServiceBrandResource(resources.ModelResource):
    class Meta:
        model = ServiceBrand
        fields = (
            "id",
            "name",
        )
        export_order = fields


class ServiceProfileResource(resources.ModelResource):
    class Meta:
        model = ServiceProfile
        # We use email as the unique identifier to find existing profiles during import
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


class CustomerMotorcycleResource(resources.ModelResource):
    # This handles the foreign key relationship to ServiceProfile
    service_profile = fields.Field(
        column_name="service_profile_email",
        attribute="service_profile",
        widget=ForeignKeyWidget(ServiceProfile, "email"),
    )

    class Meta:
        model = CustomerMotorcycle
        # We use rego (license plate) as the unique ID for motorcycles
        import_id_fields = ("rego",)
        fields = (
            "id",
            "rego",
            "vin_number",
            "brand",
            "model",
            "year",
            "service_profile",
        )
        export_order = fields


class ServiceBookingResource(resources.ModelResource):
    # Define how to handle each foreign key relationship during import/export
    service_type = fields.Field(widget=ForeignKeyWidget(ServiceType, "name"))
    service_profile = fields.Field(widget=ForeignKeyWidget(ServiceProfile, "email"))
    customer_motorcycle = fields.Field(
        widget=ForeignKeyWidget(CustomerMotorcycle, "rego")
    )

    class Meta:
        model = ServiceBooking
        import_id_fields = ("service_booking_reference",)
        fields = (
            "id",
            "service_booking_reference",
            "service_type",
            "service_profile",
            "customer_motorcycle",
            "booking_status",
            "payment_status",
            "payment_method",
            "dropoff_date",
            "dropoff_time",
            "after_hours_drop_off",
            "customer_notes",
            "calculated_total",
            "amount_paid",
        )
        export_order = fields


# --- Updated ModelAdmin Classes ---
# These classes now inherit from ImportExportModelAdmin to get the new features.


@admin.register(ServiceType)
class ServiceTypeAdmin(ImportExportModelAdmin):
    resource_class = ServiceTypeResource
    list_display = ("name", "base_price", "estimated_duration", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(CustomerMotorcycle)
class CustomerMotorcycleAdmin(ImportExportModelAdmin):
    resource_class = CustomerMotorcycleResource
    list_display = ("year", "brand", "model", "service_profile_name", "rego")
    list_filter = ("brand", "year")
    search_fields = (
        "brand",
        "model",
        "rego",
        "vin_number",
        "service_profile__name",
        "service_profile__email",
    )
    raw_id_fields = ("service_profile",)

    def service_profile_name(self, obj):
        return obj.service_profile.name if obj.service_profile else "N/A"

    service_profile_name.short_description = "Owner Name"


@admin.register(ServiceBooking)
class ServiceBookingAdmin(ImportExportModelAdmin):
    resource_class = ServiceBookingResource
    list_display = (
        "service_booking_reference",
        "service_type",
        "booking_status",
        "dropoff_date",
        "dropoff_time",
        "customer_name",
        "customer_email",
        "motorcycle_info",
        "payment_status",
    )
    list_filter = ("booking_status", "service_type", "dropoff_date", "payment_status")
    search_fields = (
        "service_booking_reference",
        "service_profile__name",
        "service_profile__email",
        "service_profile__phone_number",
        "customer_motorcycle__model",
    )
    raw_id_fields = (
        "service_type",
        "service_profile",
        "customer_motorcycle",
        "payment",
    )

    def customer_name(self, obj):
        return obj.service_profile.name if obj.service_profile else "N/A"

    customer_name.short_description = "Customer Name"

    def customer_email(self, obj):
        return obj.service_profile.email if obj.service_profile else "N/A"

    customer_email.short_description = "Customer Email"

    def motorcycle_info(self, obj):
        if obj.customer_motorcycle:
            return f"{obj.customer_motorcycle.year} {obj.customer_motorcycle.brand}"
        return "N/A"

    motorcycle_info.short_description = "Motorcycle"


@admin.register(ServiceProfile)
class ServiceProfileAdmin(ImportExportModelAdmin):
    resource_class = ServiceProfileResource
    list_display = ("name", "email", "phone_number", "city", "country", "user_link")
    list_filter = ("country", "city")
    search_fields = (
        "name",
        "email",
        "phone_number",
        "user__username",
        "city",
        "post_code",
    )
    raw_id_fields = ("user",)

    def user_link(self, obj):
        if obj.user:
            return f"{obj.user.username} (ID: {obj.user.id})"
        return "Anonymous"

    user_link.short_description = "Associated User"


@admin.register(ServiceBrand)
class ServiceBrandAdmin(ImportExportModelAdmin):
    resource_class = ServiceBrandResource
    list_display = ("name", "last_updated")
    search_fields = ("name",)


# --- Unchanged Admin Classes ---
# These models are less likely to need import/export functionality.


@admin.register(ServiceSettings)
class ServiceSettingsAdmin(admin.ModelAdmin):
    list_display = ("enable_online_deposit", "currency_code")
    list_filter = ("enable_online_deposit",)

    def has_add_permission(self, request):
        return not ServiceSettings.objects.exists()


@admin.register(BlockedServiceDate)
class BlockedServiceDateAdmin(admin.ModelAdmin):
    list_display = ("start_date", "end_date", "description")
    list_filter = ("start_date", "end_date")
    search_fields = ("description",)


@admin.register(TempServiceBooking)
class TempServiceBookingAdmin(admin.ModelAdmin):
    list_display = (
        "session_uuid",
        "service_type",
        "service_profile_name",
        "dropoff_date",
        "dropoff_time",
        "payment_method",
        "created_at",
    )
    list_filter = ("service_type", "dropoff_date", "payment_method")
    search_fields = (
        "session_uuid",
        "service_profile__name",
        "service_profile__email",
        "customer_motorcycle__model",
    )
    raw_id_fields = ("service_type", "service_profile", "customer_motorcycle")

    def service_profile_name(self, obj):
        return obj.service_profile.name if obj.service_profile else "N/A"

    service_profile_name.short_description = "Customer Name (Temp)"


@admin.register(Servicefaq)
class ServicefaqAdmin(admin.ModelAdmin):
    list_display = ("question", "booking_step", "is_active", "display_order")
    list_filter = ("booking_step", "is_active")
    search_fields = ("question", "answer")


@admin.register(ServiceTerms)
class ServiceTermsAdmin(admin.ModelAdmin):
    list_display = ("version_number", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("content",)
