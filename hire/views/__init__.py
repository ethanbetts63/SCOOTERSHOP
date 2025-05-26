# hire/views/__init__.py
from .Admin_Hire_Booking_view import AdminHireBookingView
from .step1_DateTime_view import SelectDateTimeView
from .step2_BikeChoice_view import BikeChoiceView
from .step3_AddonPackage_view import AddonPackageView
from .step4_HasAccount_view import HasAccountView
from .step4_NoAccount_view import NoAccountView
from .step5_BookSumAndPaymentOptions_view import BookSumAndPaymentOptionsView
from .step6_PaymentDetails_view import PaymentDetailsView
from .step7_BookingConfirmation_view import BookingConfirmationView, BookingStatusCheckView

# Import new functions from hire_pricing.py
from .hire_pricing import (
    calculate_motorcycle_hire_price,
    calculate_package_price,
    calculate_addon_price,
    calculate_total_addons_price,
    calculate_booking_grand_total,
)

# Import new functions from utils.py
from .utils import (
    calculate_hire_duration_days,
    get_overlapping_motorcycle_bookings,
    is_motorcycle_available,
)
