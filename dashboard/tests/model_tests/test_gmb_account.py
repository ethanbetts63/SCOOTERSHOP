import pytest
from django.utils import timezone
import factory
from dashboard.models.gmb_account import GoogleMyBusinessAccount


class GoogleMyBusinessAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GoogleMyBusinessAccount

    account_id = factory.Sequence(lambda n: f"accounts/{n}")
    location_id = factory.Sequence(lambda n: f"locations/{n}")
    access_token = factory.Faker("sha256")
    refresh_token = factory.Faker("sha256")
    token_expiry = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(hours=1))
    last_synced = factory.LazyFunction(timezone.now)


@pytest.mark.django_db
def test_google_my_business_account_singleton():
    # Create the first instance
    account1 = GoogleMyBusinessAccountFactory()
    assert GoogleMyBusinessAccount.objects.count() == 1

    # Try to create another instance, it should update the existing one
    account2 = GoogleMyBusinessAccountFactory(account_id="new_account_id", location_id="new_location_id")
    assert GoogleMyBusinessAccount.objects.count() == 1
    assert account2.pk == account1.pk
    assert GoogleMyBusinessAccount.load().account_id == "new_account_id"

    # Try saving another instance directly
    account3 = GoogleMyBusinessAccount()
    account3.account_id = "another_account_id"
    account3.save()
    assert GoogleMyBusinessAccount.objects.count() == 1
    assert GoogleMyBusinessAccount.load().account_id == "another_account_id"


@pytest.mark.django_db
def test_google_my_business_account_load_method():
    # Test load when no instance exists
    account = GoogleMyBusinessAccount.load()
    assert GoogleMyBusinessAccount.objects.count() == 1
    assert account.pk == 1

    # Test load when an instance already exists
    account.account_id = "existing_account"
    account.save()
    loaded_account = GoogleMyBusinessAccount.load()
    assert GoogleMyBusinessAccount.objects.count() == 1
    assert loaded_account.pk == account.pk
    assert loaded_account.account_id == "existing_account"


@pytest.mark.django_db
def test_google_my_business_account_is_configured_property():
    # Test when refresh_token is present
    account_configured = GoogleMyBusinessAccountFactory(refresh_token="some_token")
    assert account_configured.is_configured is True

    # Test when refresh_token is None
    account_not_configured_none = GoogleMyBusinessAccountFactory(refresh_token=None)
    assert account_not_configured_none.is_configured is False

    # Test when refresh_token is an empty string
    account_not_configured_empty = GoogleMyBusinessAccountFactory(refresh_token="")
    assert account_not_configured_empty.is_configured is False


@pytest.mark.django_db
def test_google_my_business_account_str_method():
    # Test with account_id and location_id
    account = GoogleMyBusinessAccountFactory(account_id="test_account", location_id="test_location")
    assert str(account) == "Connected GMB Account: test_account"

    # Test without account_id and location_id
    account_no_ids = GoogleMyBusinessAccountFactory(account_id=None, location_id=None)
    assert str(account_no_ids) == "No GMB Account Connected"

    account_empty_ids = GoogleMyBusinessAccountFactory(account_id="", location_id="")
    assert str(account_empty_ids) == "No GMB Account Connected"
