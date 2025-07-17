from django.test import TestCase
from django.urls import reverse
from service.tests.test_helpers.model_factories import ServiceTypeFactory
from users.tests.test_helpers.model_factories import staff_factory


class ServiceTypeManagementViewTest(TestCase):
    def setUp(self):
        self.admin_user = staff_factory()
        self.client.force_login(self.admin_user)
        self.service_type1 = ServiceTypeFactory(name="Oil Change")
        self.service_type2 = ServiceTypeFactory(name="Tyre Replacement")

    def test_get_service_type_management_view(self):
        response = self.client.get(reverse("service:service_types_management"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "service/admin_service_type_management.html")
        self.assertIn("service_types", response.context)
        self.assertEqual(
            list(response.context["service_types"]),
            [self.service_type1, self.service_type2],
        )

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse("service:service_types_management"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login")
            + "?next="
            + reverse("service:service_types_management"),
        )
