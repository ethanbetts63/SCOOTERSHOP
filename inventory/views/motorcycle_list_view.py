# inventory/views/motorcycle_list_view.py

from django.shortcuts import render, redirect
from django.views.generic import ListView
from django.db.models import Q
import datetime
from django.contrib import messages
from inventory.models import Motorcycle
from decimal import Decimal


# Base class for displaying lists of motorcycles
class MotorcycleListView(ListView):
    model = Motorcycle
    template_name = 'inventory/motorcycle_list.html'
    context_object_name = 'motorcycles'
    paginate_by = 12

    # Applies common GET parameters filters and sorting to a queryset
    def _apply_common_filters_and_sorting(self, queryset):
        brand = self.request.GET.get('brand')
        model_query = self.request.GET.get('model')
        year_min = self.request.GET.get('year_min')
        year_max = self.request.GET.get('year_max')
        price_min = self.request.GET.get('price_min')
        price_max = self.request.GET.get('price_max')

        if brand:
            # Corrected: Use iexact for case-insensitive brand filtering
            queryset = queryset.filter(brand__iexact=brand)
        if model_query:
            queryset = queryset.filter(model__icontains=model_query)
        try:
            if year_min: queryset = queryset.filter(year__gte=int(year_min))
            if year_max: queryset = queryset.filter(year__lte=int(year_max))
        except (ValueError, TypeError): pass

        try:
            # Use Decimal for price filtering
            if price_min:
                 queryset = queryset.filter(price__gte=Decimal(price_min))
            if price_max:
                 queryset = queryset.filter(price__lte=Decimal(price_max))
        # Catch potential errors from Decimal conversion as well
        except (ValueError, TypeError):
            pass

        order = self.request.GET.get('order', 'price_low_to_high')

        if order == 'price_low_to_high':
            # Handle None prices by ordering them last
            queryset = queryset.order_by('price')
        elif order == 'price_high_to_low':
            # Handle None prices by ordering them first
            queryset = queryset.order_by('-price')
        elif order == 'age_new_to_old':
            queryset = queryset.order_by('-year', '-pk')
        elif order == 'age_old_to_new':
            queryset = queryset.order_by('year', 'pk')
        else:
            queryset = queryset.order_by('price')

        return queryset

    # Builds the queryset based on filters and conditions
    def get_queryset(self):
        # Start with base queryset (available motorcycles) and apply condition filter
        # This is for the public-facing views (New, Used, Hire)
        queryset = super().get_queryset().filter(is_available=True)

        condition_name = getattr(self, 'condition_name', None) or self.kwargs.get('condition_name') or self.request.GET.get('condition')

        if condition_name:
            if condition_name.lower() == 'used':
                 queryset = queryset.filter(conditions__name__in=['used', 'demo']).distinct()
            elif condition_name.lower() in ['new', 'hire']:
                 queryset = queryset.filter(conditions__name__iexact=condition_name).distinct()

        # Apply common filters and sorting using the helper
        # Common filters (brand, model, year, price) are applied AFTER condition and availability for public views
        queryset = self._apply_common_filters_and_sorting(queryset)


        return queryset

    # Adds common context data like filters and sorting
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        condition_name = getattr(self, 'condition_name', None) or self.kwargs.get('condition_name') or self.request.GET.get('condition')

        if condition_name:
            context['condition'] = condition_name
            context['condition_lower'] = condition_name.lower()

        if hasattr(self, 'url_name'):
             context['current_url_name'] = self.url_name

        # Filter options context should reflect the base queryset before GET filters apply
        # i.e., available bikes, potentially filtered by condition_name attribute
        # This logic is for the public-facing views. AllMotorcycleListView will override this.
        filtered_for_options = Motorcycle.objects.filter(is_available=True)
        if condition_name: # Use the determined condition_name here
             if condition_name.lower() == 'used':
                  filtered_for_options = filtered_for_options.filter(conditions__name__in=['used', 'demo']).distinct()
             elif condition_name.lower() in ['new', 'hire']:
                 filtered_for_options = filtered_for_options.filter(conditions__name__iexact=condition_name).distinct()


        context['brands'] = sorted(list(filtered_for_options.values_list('brand', flat=True).distinct()))

        years = list(filtered_for_options.values_list('year', flat=True).distinct())
        if years:
            min_year = min(years)
            max_year = max(years)
            context['years'] = list(range(max_year, min_year - 1, -1))
        else:
            context['years'] = []

        context['request'] = self.request

        context['current_order'] = self.request.GET.get('order', 'price_low_to_high')

        return context