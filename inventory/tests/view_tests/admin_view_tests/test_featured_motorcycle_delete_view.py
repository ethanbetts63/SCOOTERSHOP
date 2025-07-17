from django.test import TestCase
from django.urls import reverse
from inventory.models import FeaturedMotorcycle
from inventory.tests.test_helpers.model_factories import (
    FeaturedMotorcycleFactory,
    UserFactory,
    StaffUserFactory,
)
from django.contrib.messages import get_messages


class FeaturedMotorcycleDeleteViewTest(TestCase):
    def setUp(self):
        self.admin_user = StaffUserFactory()
        self.client.force_login(self.admin_user)
        self.featured_motorcycle = FeaturedMotorcycleFactory()

    def test_delete_featured_motorcycle_post(self):
        initial_count = FeaturedMotorcycle.objects.count()
        response = self.client.post(
            reverse(
                "inventory:delete_featured_motorcycle",
                kwargs={"pk": self.featured_motorcycle.pk},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("inventory:featured_motorcycles"))
        self.assertEqual(FeaturedMotorcycle.objects.count(), initial_count - 1)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Featured motorcycle removed successfully!")

    def test_delete_nonexistent_featured_motorcycle(self):
        initial_count = FeaturedMotorcycle.objects.count()
        response = self.client.post(
            reverse("inventory:delete_featured_motorcycle", kwargs={"pk": 999})
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(FeaturedMotorcycle.objects.count(), initial_count)

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.post(
            reverse(
                "inventory:delete_featured_motorcycle",
                kwargs={"pk": self.featured_motorcycle.pk},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse(
                "inventory:delete_featured_motorcycle",
                kwargs={"pk": self.featured_motorcycle.pk},
            ),
        )
