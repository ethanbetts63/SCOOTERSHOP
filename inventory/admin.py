# inventory/admin.py

from django.contrib import admin

# Import models from the inventory app
from .models import Motorcycle, MotorcycleCondition, MotorcycleImage
from django.forms import inlineformset_factory # Import inlineformset_factory if using inlines

# Register your models here.

class MotorcycleImageInline(admin.TabularInline):
    """Inline admin for MotorcycleImage."""
    model = MotorcycleImage
    extra = 1 # Number of empty forms to display

@admin.register(Motorcycle)
class MotorcycleAdmin(admin.ModelAdmin):
    list_display = ('title', 'brand', 'model', 'year', 'price', 'is_available', 'display_conditions')
    list_filter = ('is_available', 'conditions')
    search_fields = ('title', 'brand', 'model', 'stock_number', 'rego')
    # prepopulated_fields = {'slug': ('brand', 'model', 'year')} # Assuming you have a slug field
    filter_horizontal = ('conditions',) # Use a better widget for ManyToManyField
    inlines = [MotorcycleImageInline,] # Include the image inline

    def display_conditions(self, obj):
        """Custom method to display conditions in list_display."""
        return ", ".join([condition.name for condition in obj.conditions.all()])
    display_conditions.short_description = 'Conditions'


@admin.register(MotorcycleCondition)
class MotorcycleConditionAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name')
    search_fields = ('name',)

# MotorcycleImage is managed via the inline in MotorcycleAdmin,
# so you might not need to register it separately unless you want
# a dedicated list view for images.
# @admin.register(MotorcycleImage)
# class MotorcycleImageAdmin(admin.ModelAdmin):
#     list_display = ('motorcycle', 'image')
#     list_filter = ('motorcycle',)