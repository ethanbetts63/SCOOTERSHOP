                                           

from inventory.models import Motorcycle
from django.core.exceptions import ObjectDoesNotExist

def get_motorcycle_details(pk: int):
    try:
        motorcycle = Motorcycle.objects.prefetch_related('conditions').get(pk=pk)
        return motorcycle
    except ObjectDoesNotExist:
        return None
    except Exception as e:
        return None
