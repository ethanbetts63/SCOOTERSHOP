from django.test import TestCase
from django.urls import reverse
from service.models import ServiceType
from service.tests.test_helpers.model_factories import ServiceTypeFactory
from users.tests.test_helpers.model_factories import StaffUserFactory
from django.contrib.messages import get_messages


class ServiceTypeCreateUpdateViewTest(TestCase):
    def setUp(self):
        self.admin_user = StaffUserFactory()
        self.client.force_login(self.admin_user)

    def test_create_service_type_get(self):
        response = self.client.get(reverse("service:add_service_type"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "service/admin_service_type_create_update.html"
        )
        self.assertContains(response, "Add New Service Type")
        self.assertIn("form", response.context)
        self.assertFalse(response.context["is_edit_mode"])

    def test_update_service_type_get(self):
        service_type = ServiceTypeFactory()
        response = self.client.get(
            reverse("service:edit_service_type", kwargs={"pk": service_type.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "service/admin_service_type_create_update.html"
        )
        self.assertContains(response, "Edit Service Type")
        self.assertIn("form", response.context)
        self.assertTrue(response.context["is_edit_mode"])
        self.assertEqual(response.context["current_service_type"], service_type)

    def test_create_service_type_post_success(self):
        initial_count = ServiceType.objects.count()
        data = {
            "name": "New Service",
            "description": "Description for new service",
            "base_price": 100.00,
            "is_active": True,
        }
        response = self.client.post(reverse("service:add_service_type"), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("service:service_types_management"))
        self.assertEqual(ServiceType.objects.count(), initial_count + 1)
        new_service_type = ServiceType.objects.get(name="New Service")
        self.assertIsNotNone(new_service_type)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn(
            "Service Type 'New Service' created successfully.", str(messages[0])
        )

    def test_create_service_type_post_invalid(self):
        initial_count = ServiceType.objects.count()
        data = {
            "name": "",
            "description": "Description for new service",
            "base_price": 100.00,
            "is_active": True,
        }
        response = self.client.post(reverse("service:add_service_type"), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "service/admin_service_type_create_update.html"
        )
        self.assertContains(response, "Please correct the errors below.")
        self.assertIn("form", response.context)
        self.assertFalse(response.context["form"].is_valid())
        self.assertEqual(ServiceType.objects.count(), initial_count)

    def test_update_service_type_post_success(self):
        service_type = ServiceTypeFactory(name="Original Name")
        data = {
            "name": "Updated Service",
            "description": service_type.description,
            "base_price": service_type.base_price,
            "is_active": service_type.is_active,
        }
        response = self.client.post(
            reverse("service:edit_service_type", kwargs={"pk": service_type.pk}),
            data=data,
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("service:service_types_management"))
        service_type.refresh_from_db()
        self.assertEqual(service_type.name, "Updated Service")
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn(
            "Service Type 'Updated Service' updated successfully.", str(messages[0])
        )

    def test_update_service_type_post_invalid(self):
        service_type = ServiceTypeFactory(name="Original Name")
        data = {
            "name": "",
            "description": service_type.description,
            "base_price": service_type.base_price,
            "is_active": service_type.is_active,
        }
        response = self.client.post(
            reverse("service:edit_service_type", kwargs={"pk": service_type.pk}),
            data=data,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "service/admin_service_type_create_update.html"
        )
        self.assertContains(response, "Please correct the errors below.")
        self.assertIn("form", response.context)
        self.assertFalse(response.context["form"].is_valid())

    def test_admin_required_mixin(self):
        self.client.logout()
        response = self.client.get(reverse("service:add_service_type"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login") + "?next=" + reverse("service:add_service_type"),
        )
