from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
import uuid

from service.models import CustomerMotorcycle, ServiceType, ServiceBooking
from users.models import User
from inventory.models import Motorcycle


class CustomerMotorcycleTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword',
            first_name='Test',
            last_name='User'
        )

        self.motorcycle = CustomerMotorcycle.objects.create(
            owner=self.user,
            make="Honda",
            model="CBR500R",
            year=2020,
            vin_number="ABC123456789",
            engine_number="ENG123456",
            rego="ABC123",
            odometer=12000,
            transmission="manual"
        )

    # Test that a customer motorcycle can be created with all fields
    def test_customer_motorcycle_creation(self):
        self.assertEqual(self.motorcycle.make, "Honda")
        self.assertEqual(self.motorcycle.model, "CBR500R")
        self.assertEqual(self.motorcycle.year, 2020)
        self.assertEqual(self.motorcycle.vin_number, "ABC123456789")
        self.assertEqual(self.motorcycle.engine_number, "ENG123456")
        self.assertEqual(self.motorcycle.rego, "ABC123")
        self.assertEqual(self.motorcycle.odometer, 12000)
        self.assertEqual(self.motorcycle.transmission, "manual")
        self.assertEqual(self.motorcycle.owner, self.user)

    # Test the string representation of a customer motorcycle
    def test_customer_motorcycle_string_representation(self):
        expected_string = "2020 Honda CBR500R (owned by Test User)"
        self.assertEqual(str(self.motorcycle), expected_string)

    # Test that a customer motorcycle can be created with only required fields
    def test_customer_motorcycle_with_minimal_fields(self):
        minimal_motorcycle = CustomerMotorcycle.objects.create(
            owner=self.user,
            make="Yamaha",
            model="MT-07",
            year=2019
        )
        self.assertEqual(minimal_motorcycle.make, "Yamaha")
        self.assertEqual(minimal_motorcycle.model, "MT-07")
        self.assertEqual(minimal_motorcycle.year, 2019)
        self.assertIsNone(minimal_motorcycle.vin_number)
        self.assertIsNone(minimal_motorcycle.engine_number)
        self.assertIsNone(minimal_motorcycle.rego)
        self.assertIsNone(minimal_motorcycle.odometer)
        self.assertIsNone(minimal_motorcycle.transmission)


class ServiceTypeTest(TestCase):

    def setUp(self):
        self.service_type = ServiceType.objects.create(
            name="Oil Change",
            description="Standard oil change service",
            estimated_duration=timedelta(hours=1),
            base_price=Decimal('49.99'),
            is_active=True
        )

    # Test that a service type can be created with all fields
    def test_service_type_creation(self):
        self.assertEqual(self.service_type.name, "Oil Change")
        self.assertEqual(self.service_type.description, "Standard oil change service")
        self.assertEqual(self.service_type.estimated_duration, timedelta(hours=1))
        self.assertEqual(self.service_type.base_price, Decimal('49.99'))
        self.assertTrue(self.service_type.is_active)

    # Test the string representation of a service type
    def test_service_type_string_representation(self):
        self.assertEqual(str(self.service_type), "Oil Change")

    # Test creating an inactive service type
    def test_inactive_service_type(self):
        inactive_service = ServiceType.objects.create(
            name="Deprecated Service",
            description="This service is no longer offered",
            estimated_duration=timedelta(hours=2),
            base_price=Decimal('99.99'),
            is_active=False
        )
        self.assertFalse(inactive_service.is_active)


class ServiceBookingTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testcustomer',
            email='customer@example.com',
            password='testpassword',
            first_name='Test',
            last_name='Customer'
        )

        self.motorcycle = CustomerMotorcycle.objects.create(
            owner=self.user,
            make="Kawasaki",
            model="Ninja 650",
            year=2021,
            vin_number="XYZ987654321",
            rego="XYZ987",
        )

        self.service_type = ServiceType.objects.create(
            name="Full Service",
            description="Complete motorcycle maintenance",
            estimated_duration=timedelta(hours=3),
            base_price=Decimal('149.99'),
            is_active=True
        )

        self.appointment_time = timezone.now() + timedelta(days=7)

        self.booking = ServiceBooking.objects.create(
            customer=self.user,
            vehicle=self.motorcycle,
            service_type=self.service_type,
            appointment_date=self.appointment_time,
            customer_notes="Please check brakes too",
            # preferred_contact field was removed
            status="confirmed",
            parts_cost=Decimal('75.50'),
            labor_cost=Decimal('120.00'),
            customer_address="123 Main St", # Added customer_address
            anon_vehicle_vin_number="VIN12345", # Added anon_vehicle_vin_number
            anon_engine_number="ENG7890", # Added anon_engine_number
        )

    # Test that a service booking can be created with all fields
    def test_service_booking_creation(self):
        self.assertEqual(self.booking.customer, self.user)
        self.assertEqual(self.booking.vehicle, self.motorcycle)
        self.assertEqual(self.booking.service_type, self.service_type)
        self.assertEqual(self.booking.appointment_date, self.appointment_time)
        self.assertEqual(self.booking.customer_notes, "Please check brakes too")
        # preferred_contact field was removed, so no assertion needed
        self.assertEqual(self.booking.status, "confirmed")
        self.assertEqual(self.booking.parts_cost, Decimal('75.50'))
        self.assertEqual(self.booking.labor_cost, Decimal('120.00'))
        self.assertEqual(self.booking.total_cost, Decimal('195.50'))
        self.assertEqual(self.booking.customer_address, "123 Main St") # Assert customer_address
        self.assertEqual(self.booking.anon_vehicle_vin_number, "VIN12345") # Assert anon_vehicle_vin_number
        self.assertEqual(self.booking.anon_engine_number, "ENG7890") # Assert anon_engine_number


    # Test that a booking reference is automatically generated
    def test_booking_reference_generation(self):
        self.assertIsNotNone(self.booking.booking_reference)
        self.assertTrue(self.booking.booking_reference.startswith("SRV-"))
        self.assertEqual(len(self.booking.booking_reference), 12)

    # Test the string representation of a service booking
    def test_service_booking_string_representation(self):
        # The string representation depends on whether it's an anon booking or user booking
        # This test is for a user booking with a linked vehicle
        expected_str = f"Service: Full Service for Test Customer for 2021 Kawasaki Ninja 650 (owned by Test Customer) - {self.appointment_time.strftime('%Y-%m-%d %H:%M')} (confirmed)"
        self.assertEqual(str(self.booking), expected_str)

    # Test creating a booking for an anonymous customer
    def test_anonymous_booking(self):
        anon_booking = ServiceBooking.objects.create(
            customer=None, # Explicitly set customer to None for anonymous
            customer_name="Jane Smith",
            customer_phone="555-1234",
            customer_email="jane@example.com",
            customer_address="123 Main St, Anytown", # Added customer_address
            anon_vehicle_make="Suzuki",
            anon_vehicle_model="GSX-R750",
            anon_vehicle_year=2022,
            anon_vehicle_rego="SUZ750",
            anon_vehicle_vin_number="ANONVIN123", # Added anon_vehicle_vin_number
            anon_vehicle_odometer=3000,
            anon_vehicle_transmission="manual",
            anon_engine_number="ANONENG456", # Added anon_engine_number
            service_type=self.service_type,
            appointment_date=self.appointment_time,
            # preferred_contact field was removed
            status="pending"
        )

        self.assertIsNone(anon_booking.customer)
        self.assertEqual(anon_booking.customer_name, "Jane Smith")
        self.assertEqual(anon_booking.customer_phone, "555-1234")
        self.assertEqual(anon_booking.customer_email, "jane@example.com")
        self.assertEqual(anon_booking.customer_address, "123 Main St, Anytown") # Assert customer_address
        self.assertIsNone(anon_booking.vehicle) # Ensure vehicle is None for anonymous
        self.assertEqual(anon_booking.anon_vehicle_make, "Suzuki")
        self.assertEqual(anon_booking.anon_vehicle_model, "GSX-R750")
        self.assertEqual(anon_booking.anon_vehicle_year, 2022)
        self.assertEqual(anon_booking.anon_vehicle_rego, "SUZ750")
        self.assertEqual(anon_booking.anon_vehicle_vin_number, "ANONVIN123") # Assert anon_vehicle_vin_number
        self.assertEqual(anon_booking.anon_vehicle_odometer, 3000)
        self.assertEqual(anon_booking.anon_vehicle_transmission, "manual")
        self.assertEqual(anon_booking.anon_engine_number, "ANONENG456") # Assert anon_engine_number
        self.assertEqual(anon_booking.service_type, self.service_type)
        self.assertEqual(anon_booking.appointment_date, self.appointment_time)
        # preferred_contact field was removed, so no assertion needed
        self.assertEqual(anon_booking.status, "pending")
        self.assertIsNotNone(anon_booking.booking_reference)

    # Test total cost calculation with only parts cost
    def test_cost_calculation_only_parts(self):
        parts_only_booking = ServiceBooking.objects.create(
            customer=self.user,
            service_type=self.service_type,
            appointment_date=self.appointment_time,
            parts_cost=Decimal('50.00'),
            labor_cost=None,
            customer_name="Test User", # Minimal required fields for booking
            anon_vehicle_make="Test",
            anon_vehicle_model="Bike",
            anon_vehicle_year=2000,
        )
        self.assertEqual(parts_only_booking.total_cost, Decimal('50.00'))

    # Test total cost calculation with only labor cost
    def test_cost_calculation_only_labor(self):
        labor_only_booking = ServiceBooking.objects.create(
            customer=self.user,
            service_type=self.service_type,
            appointment_date=self.appointment_time,
            parts_cost=None,
            labor_cost=Decimal('75.00'),
             customer_name="Test User", # Minimal required fields for booking
            anon_vehicle_make="Test",
            anon_vehicle_model="Bike",
            anon_vehicle_year=2000,
        )
        self.assertEqual(labor_only_booking.total_cost, Decimal('75.00'))

    # Test that total cost is None when no costs are provided
    def test_no_cost_calculation(self):
        no_cost_booking = ServiceBooking.objects.create(
            customer=self.user,
            service_type=self.service_type,
            appointment_date=self.appointment_time,
            parts_cost=None,
            labor_cost=None,
             customer_name="Test User", # Minimal required fields for booking
            anon_vehicle_make="Test",
            anon_vehicle_model="Bike",
            anon_vehicle_year=2000,
        )
        self.assertIsNone(no_cost_booking.total_cost)

    # Test updating costs recalculates the total
    def test_update_costs(self):
        self.booking.parts_cost = Decimal('100.00')
        self.booking.labor_cost = Decimal('150.00')
        self.booking.save()
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.total_cost, Decimal('250.00'))