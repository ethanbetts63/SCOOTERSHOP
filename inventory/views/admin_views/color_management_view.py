from inventory.mixins import AdminRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db import transaction

from inventory.models.color import Color
from inventory.forms.color_form import ColorForm


class ColorManagementView(AdminRequiredMixin, View):
    template_name = "inventory/color_management.html"
    form_class = ColorForm

    def get_context_data(self, form=None, edit_color=None):
        colors = Color.objects.all().order_by("name")

        if form is None:
            form = self.form_class(instance=edit_color)

        context = {
            "form": form,
            "edit_color": edit_color,
            "colors": colors,
            "page_title": "Manage Colors",
        }
        return context

    def get(self, request, *args, **kwargs):
        if not Color.objects.exists():
            self.create_initial_colors()
        edit_color_pk = request.GET.get("edit_color_pk")
        edit_color = None
        if edit_color_pk:
            edit_color = get_object_or_404(Color, pk=edit_color_pk)

        context = self.get_context_data(edit_color=edit_color)
        return render(request, self.template_name, context)

    def create_initial_colors(self):
        initial_colors = [
            "Black", "White", "Silver", "Gray", "Red",
            "Blue", "Green", "Yellow", "Orange", "Brown"
        ]
        for color_name in initial_colors:
            Color.objects.get_or_create(name=color_name)

    def post(self, request, *args, **kwargs):
        form = None
        edit_color = None

        if "add_color_submit" in request.POST:
            color_id = request.POST.get("color_id")
            if color_id:
                edit_color = get_object_or_404(Color, pk=color_id)
                form = self.form_class(request.POST, instance=edit_color)
            else:
                form = self.form_class(request.POST)

            if form.is_valid():
                try:
                    with transaction.atomic():
                        color = form.save()

                    action = "updated" if color_id else "added"
                    messages.success(
                        self.request,
                        f"Color '{color.name}' {action} successfully.",
                    )
                    return redirect("inventory:color_management")
                except ValueError as e:
                    messages.error(self.request, str(e))
                except Exception as e:
                    messages.error(self.request, f"Error saving color: {e}")
            else:
                messages.error(self.request, "Please correct the errors below.")

        context = self.get_context_data(form=form, edit_color=edit_color)
        return render(request, self.template_name, context)
