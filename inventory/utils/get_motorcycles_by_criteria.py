from django.db.models import Q
from inventory.models import Motorcycle, MotorcycleCondition


def get_motorcycles_by_criteria(
    condition_slug=None,
    brand=None,
    model=None,
    year_min=None,
    year_max=None,
    price_min=None,
    price_max=None,
    engine_min_cc=None,
    engine_max_cc=None,
    order=None,
):

    queryset = Motorcycle.objects.all()

    if condition_slug == "new":

        queryset = queryset.filter(conditions__name="new").distinct()
    elif condition_slug == "used":

        queryset = queryset.filter(
            Q(conditions__name="used") | Q(conditions__name="demo")
        ).distinct()
    elif condition_slug and condition_slug != "all":

        queryset = queryset.filter(conditions__name=condition_slug).distinct()

    if brand:
        queryset = queryset.filter(brand=brand)
    if model:
        queryset = queryset.filter(model__icontains=model)

    if year_min:
        queryset = queryset.filter(year__gte=year_min)
    if year_max:
        queryset = queryset.filter(year__lte=year_max)

    if price_min is not None:
        queryset = queryset.filter(price__gte=price_min)
    if price_max is not None:
        queryset = queryset.filter(price__lte=price_max)

    if engine_min_cc is not None:
        queryset = queryset.filter(engine_size__gte=engine_min_cc)
    if engine_max_cc is not None:
        queryset = queryset.filter(engine_size__lte=engine_max_cc)

    if order == "price_low_to_high":
        queryset = queryset.order_by("price")
    elif order == "price_high_to_low":
        queryset = queryset.order_by("-price")
    elif order == "age_new_to_old":
        queryset = queryset.order_by("-year", "-date_posted")
    elif order == "age_old_to_new":
        queryset = queryset.order_by("year", "date_posted")
    else:

        queryset = queryset.order_by("-date_posted")

    return queryset
