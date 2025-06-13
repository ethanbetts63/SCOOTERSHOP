# inventory_app/utils/motorcycle_filters.py

from ..models import Motorcycle, MotorcycleCondition
from django.db.models.query import QuerySet

def get_motorcycles_by_criteria(
    condition_slug = None,
    year_min = None,
    year_max = None,
    engine_min_cc = None,
    engine_max_cc = None,
    price_min = None,
    price_max = None,
    makes = None,
):
    motorcycles = Motorcycle.objects.all()

    if condition_slug:
        try:
            condition_obj = MotorcycleCondition.objects.get(display_name__iexact=condition_slug)
            motorcycles = motorcycles.filter(condition=condition_obj)
        except MotorcycleCondition.DoesNotExist:
            return Motorcycle.objects.none()

    if year_min is not None:
        motorcycles = motorcycles.filter(year__gte=year_min)
    if year_max is not None:
        motorcycles = motorcycles.filter(year__lte=year_max)

    if engine_min_cc is not None:
        motorcycles = motorcycles.filter(engine_size_cc__gte=engine_min_cc)
    if engine_max_cc is not None:
        motorcycles = motorcycles.filter(engine_size_cc__lte=engine_max_cc)

    if price_min is not None:
        motorcycles = motorcycles.filter(price__gte=price_min)
    if price_max is not None:
        motorcycles = motorcycles.filter(price__lte=price_max)

    if makes:
        motorcycles = motorcycles.filter(brand__in=makes)

    return motorcycles.order_by('brand', 'model', 'year')
