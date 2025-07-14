import factory
from django.contrib.auth import get_user_model
from dashboard.models import SiteSettings

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker("uuid4")
    email = factory.Faker("email")
    password = factory.PostGenerationMethodCall('set_password', 'testpassword')
    is_active = True
    is_staff = False
    is_superuser = False

class StaffUserFactory(UserFactory):
    is_staff = True

class SiteSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SiteSettings

    enable_sales_new = True
    enable_sales_used = True
    enable_service_booking = True
    enable_user_accounts = True
    enable_contact_page = True
    enable_map_display = True
    enable_privacy_policy_page = True
    enable_returns_page = True
    enable_security_page = True
    enable_google_places_reviews = True
    phone_number = "(08) 9433 4613"
    email_address = "admin@scootershop.com.au"
    street_address = "Unit 2/95 Queen Victoria St"
    address_locality = "Fremantle"
    address_region = "WA"
    postal_code = "6160"
    google_places_place_id = "ChIJy_zrHmGhMioRisz6mis0SpQ"
    opening_hours_monday = "10:30am to 5:00pm"
    opening_hours_tuesday = "10:30am to 5:00pm"
    opening_hours_wednesday = "10:30am to 5:00pm"
    opening_hours_thursday = "10:30am to 5:00pm"
    opening_hours_friday = "10:30am to 5:00pm"
    opening_hours_saturday = "10:30am to 1:00pm (By Appointment only)"
    opening_hours_sunday = "Closed"
