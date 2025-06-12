# # inventory/views/motorcycle_form_handler_mixin.py

# from django.shortcuts import render
# from django.contrib import messages
# from inventory.models import MotorcycleImage
# from inventory.forms import MotorcycleImageFormSet


# class MotorcycleFormHandlerMixin:
#     """Mixin to handle saving the main form and the image formset."""
#     def form_valid(self, form):
#         """
#         Handles the valid main form and validates/saves the image formset.
#         """
#         context = self.get_context_data()
#         images_formset = context['images_formset']

#         # Ensure the formset is bound to the form instance before validation
#         # This is crucial for inline formsets, especially in update views
#         if self.object: # Check if we have an instance (UpdateView)
#              images_formset.instance = self.object

#         # --- MODIFIED: Check if the formset is valid BEFORE saving anything ---
#         # If the formset is not valid, we stop here and render the form with errors.
#         if images_formset.is_valid():
#             # Both main form and formset are valid. Proceed with saving.

#             # Save the main form first to get the instance (required for formset)
#             self.object = form.save()

#             # Handle multiple uploaded files from the 'additional_images' input
#             # This input is separate from the formset and handles new uploads
#             additional_images = self.request.FILES.getlist('additional_images')
#             for image_file in additional_images:
#                 if image_file: # Ensure there's actually a file
#                     try:
#                         MotorcycleImage.objects.create(
#                             motorcycle=self.object,
#                             image=image_file
#                         )
#                     except Exception as e:
#                         # Log or add a message if a file upload fails
#                         messages.error(self.request, f"Failed to upload image {image_file.name}: {e}")
#                         print(f"Error uploading image {image_file.name}: {e}")


#             # Process the formset for existing images (for deletions and changes)
#             # Link the formset to the saved motorcycle instance
#             images_formset.instance = self.object
#             # Save the formset - this handles deletions and changes to existing images
#             try:
#                 images_formset.save()
#             except Exception as e:
#                  # Catch potential errors during formset save
#                  messages.error(self.request, f"Error saving image changes: {e}")
#                  print(f"Error saving image formset: {e}")
#                  # You might want to redirect or re-render here depending on desired behavior
#                  # For now, we'll let the main form's success_url handle redirection,
#                  # but the error message will be displayed.

#             # Proceed with the default form_valid behavior (redirect to success_url)
#             return super().form_valid(form)
#         else:
#             # --- MODIFIED: If the formset is NOT valid, render the form with errors ---
#             # This prevents the AttributeError by not attempting to save an invalid formset.
#             # The formset errors will be available in the context and displayed in the template.
#             print(f"Image formset is invalid: {images_formset.errors}") # Log formset errors
#             # Add formset errors to messages for user feedback
#             # Iterate through formset errors (errors is a list of dicts, one dict per form)
#             for i, formset_form_errors in enumerate(images_formset.errors):
#                  if formset_form_errors: # Check if the form has errors
#                      messages.error(self.request, f"Error in Image Form #{i+1}:")
#                      for field, errors in formset_form_errors.items():
#                           for error in errors:
#                                messages.error(self.request, f"- {field}: {error}")

#             # Add non-field errors for the formset itself
#             for error in images_formset.non_form_errors():
#                  messages.error(self.request, f"Image formset error: {error}")

#             # Render the template with the valid main form and the invalid formset
#             context['form'] = form # Ensure the valid main form is in context
#             # The formset is already in context from get_context_data
#             return render(self.request, self.template_name, context)


#     def form_invalid(self, form):
#         """
#         Handles the invalid main form.
#         """
#         # Include formset in context when the main form is invalid
#         context = self.get_context_data()
#         context['form'] = form # Ensure the invalid main form is in context
#         # The formset is already added in get_context_data if request is POST

#         # Add formset errors to messages if any (already handled in form_valid, but good to be safe)
#         if 'images_formset' in context and context['images_formset'].errors:
#              for i, formset_form_errors in enumerate(context['images_formset'].errors):
#                  if formset_form_errors:
#                      messages.error(self.request, f"Error in Image Form #{i+1}:")
#                      for field, errors in formset_form_errors.items():
#                           for error in errors:
#                                messages.error(self.request, f"- {field}: {error}")
#              for error in context['images_formset'].non_form_errors():
#                   messages.error(self.request, f"Image formset error: {error}")


#         # Render the template with the invalid main form and the formset
#         return render(self.request, self.template_name, context)


#     def get_context_data(self, **kwargs):
#         """
#         Adds the image formset to the context.
#         """
#         context = super().get_context_data(**kwargs)
#         # Pass the instance to the formset for UpdateView
#         instance = self.object if hasattr(self, 'object') else None

#         if self.request.method == 'POST':
#             # If POST, populate formset with data and files
#             context['images_formset'] = MotorcycleImageFormSet(self.request.POST, self.request.FILES, instance=instance)
#         else:
#             # If GET, populate formset with existing images if instance exists
#             context['images_formset'] = MotorcycleImageFormSet(instance=instance)

#         return context