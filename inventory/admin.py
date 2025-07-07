from django.contrib import admin
from .models.blocked_sales_date import BlockedSalesDate
from .models.featured_motorcycle import FeaturedMotorcycle
from .models.inventory_settings import InventorySettings
from .models.motorcycle import Motorcycle
from .models.motorcycle_condition import MotorcycleCondition
from .models.motorcycle_image import MotorcycleImage
from .models.sales_booking import SalesBooking
from .models.sales_faq import Salesfaq
from .models.sales_profile import SalesProfile
from .models.sales_terms import SalesTerms
from .models.temp_sales_booking import TempSalesBooking

admin.site.register(BlockedSalesDate)
admin.site.register(FeaturedMotorcycle)
admin.site.register(InventorySettings)
admin.site.register(Motorcycle)
admin.site.register(MotorcycleCondition)
admin.site.register(MotorcycleImage)
admin.site.register(SalesBooking)
admin.site.register(Salesfaq)
admin.site.register(SalesProfile)
admin.site.register(SalesTerms)
admin.site.register(TempSalesBooking)
