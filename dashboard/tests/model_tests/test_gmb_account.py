from django.test import TestCase
from django.utils import timezone
import factory
from dashboard.models.gmb_account import GoogleMyBusinessAccount


class GoogleMyBusinessAccountFactory(factory.Factory):
    class Meta:
        model = GoogleMyBusinessAccount

    account_id = factory.Sequence(lambda n: f"accounts/{n}")
    location_id = factory.Sequence(lambda n: f"locations/{n}")
    access_token = factory.Faker("sha256")
    refresh_token = factory.Faker("sha256")
    token_expiry = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(hours=1))
    last_synced = factory.LazyFunction(timezone.now)


class GoogleMyBusinessAccountModelTest(TestCase):

    def setUp(self):
        # Ensure a clean state for each test by deleting any existing instance
        # and then loading the singleton to ensure it's ready for modification.
        GoogleMyBusinessAccount.objects.all().delete()
        self.gmb_account = GoogleMyBusinessAccount.load()

    def test_google_my_business_account_singleton(self):
        # Verify that load() always returns the same instance
        account1 = GoogleMyBusinessAccount.load()
        account1.account_id = "initial_account_id"
        account1.save()
        self.assertEqual(GoogleMyBusinessAccount.objects.count(), 1)
        self.assertEqual(GoogleMyBusinessAccount.load().account_id, "initial_account_id")

        # Try to get another instance using load(), it should return the existing one
        account2 = GoogleMyBusinessAccount.load()
        account2.account_id = "updated_account_id"
        account2.save()
        self.assertEqual(GoogleMyBusinessAccount.objects.count(), 1)
        self.assertEqual(account2.pk, account1.pk)
        self.assertEqual(GoogleMyBusinessAccount.load().account_id, "updated_account_id")

        # Verify that direct creation attempts also respect the singleton (by updating pk=1)
        # This test case is tricky because the model's save method forces pk=1.
        # We'll test that if we try to create a new one, it just updates the existing one.
        new_data = GoogleMyBusinessAccountFactory.build(
            account_id="another_account_id",
            location_id="another_location_id",
            access_token="abc",
            refresh_token="def",
            token_expiry=timezone.now()
        )
        new_data.save() # This will update the existing singleton instance
        self.assertEqual(GoogleMyBusinessAccount.objects.count(), 1)
        self.assertEqual(GoogleMyBusinessAccount.load().account_id, "another_account_id")

    def test_google_my_business_account_load_method(self):
        # Test load when no instance exists (handled by setUp, but re-verify)
        self.assertEqual(GoogleMyBusinessAccount.objects.count(), 1)
        self.assertEqual(self.gmb_account.pk, 1)

        # Test load when an instance already exists
        self.gmb_account.account_id = "existing_account"
        self.gmb_account.save()
        loaded_account = GoogleMyBusinessAccount.load()
        self.assertEqual(GoogleMyBusinessAccount.objects.count(), 1)
        self.assertEqual(loaded_account.pk, self.gmb_account.pk)
        self.assertEqual(loaded_account.account_id, "existing_account")

    def test_google_my_business_account_is_configured_property(self):
        # Test when refresh_token is present
        self.gmb_account.refresh_token = "some_token"
        self.gmb_account.save()
        self.assertTrue(self.gmb_account.is_configured)

        # Test when refresh_token is None
        self.gmb_account.refresh_token = None
        self.gmb_account.save()
        self.assertFalse(self.gmb_account.is_configured)

        # Test when refresh_token is an empty string
        self.gmb_account.refresh_token = ""
        self.gmb_account.save()
        self.assertFalse(self.gmb_account.is_configured)

    def test_google_my_business_account_str_method(self):
        # Test with account_id and location_id
        self.gmb_account.account_id = "test_account"
        self.gmb_account.location_id = "test_location"
        self.gmb_account.save()
        self.assertEqual(str(self.gmb_account), "Connected GMB Account: test_account")

        # Test without account_id and location_id
        self.gmb_account.account_id = None
        self.gmb_account.location_id = None
        self.gmb_account.save()
        self.assertEqual(str(self.gmb_account), "No GMB Account Connected")

        self.gmb_account.account_id = ""
        self.gmb_account.location_id = ""
        self.gmb_account.save()
        self.assertEqual(str(self.gmb_account), "No GMB Account Connected")
