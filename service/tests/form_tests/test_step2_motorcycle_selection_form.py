from django.test import TestCase
from django.core.exceptions import ValidationError

# Import the form and the sentinel value
from service.forms import MotorcycleSelectionForm, ADD_NEW_MOTORCYCLE_OPTION

# Import factories for related models
from ..test_helpers.model_factories import ServiceProfileFactory, CustomerMotorcycleFactory

class MotorcycleSelectionFormTest(TestCase):
    """
    Tests for the MotorcycleSelectionForm.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        Updated to remove 'make' and include all required fields for CustomerMotorcycleFactory.
        """
        cls.service_profile_with_bikes = ServiceProfileFactory()
        cls.motorcycle1 = CustomerMotorcycleFactory(
            service_profile=cls.service_profile_with_bikes,
            brand="Honda",
            # Removed 'make'
            model="600RR",
            rego="ABC123",
            odometer=10000, # Added required odometer
            transmission="MANUAL", # Added required transmission
            engine_size="600cc", # Added required engine_size
        )
        cls.motorcycle2 = CustomerMotorcycleFactory(
            service_profile=cls.service_profile_with_bikes,
            brand="Yamaha",
            # Removed 'make'
            model="R1",
            rego="XYZ789",
            odometer=12000, # Added required odometer
            transmission="MANUAL", # Added required transmission
            engine_size="1000cc", # Added required engine_size
        )

        cls.service_profile_no_bikes = ServiceProfileFactory()

    def test_form_initialization_with_motorcycles(self):
        """
        Test that the form initializes correctly with existing motorcycles
        for a service profile.
        Updated to reflect removal of 'make' in string representation.
        """
        form = MotorcycleSelectionForm(service_profile=self.service_profile_with_bikes)
        choices = form.fields['selected_motorcycle'].choices

        # Expected choices: ('add_new', '--- Add a New Motorcycle ---')
        # and then the existing motorcycles
        self.assertEqual(len(choices), 3) # Add New + 2 motorcycles

        # Check the 'Add New' option
        self.assertEqual(choices[0], (ADD_NEW_MOTORCYCLE_OPTION, "--- Add a New Motorcycle ---"))

        # Check existing motorcycles - updated to reflect removal of 'make'
        self.assertIn((str(self.motorcycle1.pk), f"{self.motorcycle1.brand} {self.motorcycle1.model} ({self.motorcycle1.rego})"), choices)
        self.assertIn((str(self.motorcycle2.pk), f"{self.motorcycle2.brand} {self.motorcycle2.model} ({self.motorcycle2.rego})"), choices)

        # Initial should not be set if motorcycles exist (or should be 'add_new' if explicitly desired, but default is usually first option)
        # Based on the form's __init__, initial is only set to ADD_NEW_MOTORCYCLE_OPTION if not motorcycles.
        self.assertIsNone(form.fields['selected_motorcycle'].initial)


    def test_form_initialization_without_motorcycles(self):
        """
        Test that the form initializes correctly when no motorcycles exist
        for a service profile, and 'Add New' is the default.
        """
        form = MotorcycleSelectionForm(service_profile=self.service_profile_no_bikes)
        choices = form.fields['selected_motorcycle'].choices

        # Expected choices: only ('add_new', '--- Add a New Motorcycle ---')
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0], (ADD_NEW_MOTORCYCLE_OPTION, "--- Add a New Motorcycle ---"))

        # 'Add New' should be the initial selected option
        self.assertEqual(form.fields['selected_motorcycle'].initial, ADD_NEW_MOTORCYCLE_OPTION)

    def test_form_valid_data_select_existing_motorcycle(self):
        """
        Test that the form is valid when an existing motorcycle is selected.
        """
        form = MotorcycleSelectionForm(
            service_profile=self.service_profile_with_bikes,
            data={'selected_motorcycle': str(self.motorcycle1.pk)}
        )
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['selected_motorcycle'], str(self.motorcycle1.pk))

    def test_form_valid_data_select_add_new(self):
        """
        Test that the form is valid when 'Add New Motorcycle' is selected.
        """
        form = MotorcycleSelectionForm(
            service_profile=self.service_profile_with_bikes, # Can still have bikes, but user chooses 'add_new'
            data={'selected_motorcycle': ADD_NEW_MOTORCYCLE_OPTION}
        )
        self.assertTrue(form.is_valid(), f"Form is not valid: {form.errors}")
        self.assertEqual(form.cleaned_data['selected_motorcycle'], ADD_NEW_MOTORCYCLE_OPTION)

    def test_form_invalid_data_missing_selection(self):
        """
        Test that the form is invalid if no selection is made (required field).
        """
        form = MotorcycleSelectionForm(
            service_profile=self.service_profile_with_bikes,
            data={'selected_motorcycle': ''} # Empty selection
        )
        self.assertFalse(form.is_valid())
        self.assertIn('selected_motorcycle', form.errors)
        self.assertIn('This field is required.', form.errors['selected_motorcycle'])

    def test_form_invalid_data_non_existent_motorcycle_id_format(self):
        """
        Test that the form is invalid if a non-integer string is submitted,
        which should trigger ChoiceField's validation.
        """
        form = MotorcycleSelectionForm(
            service_profile=self.service_profile_with_bikes,
            data={'selected_motorcycle': 'not-an-id'}
        )
        self.assertFalse(form.is_valid())
        self.assertIn('selected_motorcycle', form.errors)
        # Assert the expected error message from ChoiceField validation
        self.assertIn('Select a valid choice. not-an-id is not one of the available choices.', form.errors['selected_motorcycle'])

    def test_form_invalid_data_unowned_motorcycle_id(self):
        """
        Test that the form is INVALID if a valid integer ID is submitted
        that does not belong to the user's ServiceProfile, because the form's
        choices are dynamically filtered by the service_profile.
        Ensure all required fields are provided when creating `unowned_motorcycle`.
        """
        # Create a motorcycle belonging to a *different* service profile
        unowned_motorcycle = CustomerMotorcycleFactory(
            brand="Kawasaki", model="Ninja", year=2022, rego="KLM789", odometer=15000,
            transmission="MANUAL", engine_size="400cc"
        )
        
        form = MotorcycleSelectionForm(
            service_profile=self.service_profile_with_bikes, # Form initialized with THIS profile's bikes
            data={'selected_motorcycle': str(unowned_motorcycle.pk)} # Submitting an ID NOT in the choices
        )
        # The form should now be INVALID because the unowned_motorcycle.pk
        # is not in the choices generated for self.service_profile_with_bikes.
        self.assertFalse(form.is_valid())
        self.assertIn('selected_motorcycle', form.errors)
        # The error message will be the standard ChoiceField one
        self.assertIn(f'Select a valid choice. {unowned_motorcycle.pk} is not one of the available choices.', form.errors['selected_motorcycle'])

