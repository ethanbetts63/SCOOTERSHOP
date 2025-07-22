import factory
import factory.fuzzy
from factory.faker import Faker
from dashboard.models import SiteSettings, Review


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
    phone_number = "94334613"
    email_address = "admin@scootershop.com.au"
    street_address = "Unit 5 / 6 Cleveland Street"
    address_locality = "Dianella"
    address_region = "WA"
    postal_code = "6059"
    google_places_place_id = "ChIJy_zrHmGhMioRisz6mis0SpQ"
    mrb_number = "MRB5092"
    abn_number = "46157594161"
    md_number = "28276"
    opening_hours_monday = "10:30am to 5:00pm"
    opening_hours_tuesday = "10:30am to 5:00pm"
    opening_hours_wednesday = "10:30am to 5:00pm"
    opening_hours_thursday = "10:30am to 5:00pm"
    opening_hours_friday = "10:30am to 5:00pm"
    opening_hours_saturday = "10:30am to 1:00pm (By Appointment only)"
    opening_hours_sunday = "Closed"
    enable_motorcycle_mover=True,
    enable_frank=True,
    enable_banner=True,
    banner_text = ""


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review

    author_name = Faker('name')
    rating = factory.fuzzy.FuzzyInteger(1, 5)
    text = Faker('text')
    profile_photo_url = factory.Faker('image_url')
    display_order = factory.Sequence(lambda n: n)
    is_active = True