
from django.core.exceptions import ObjectDoesNotExist
from inventory.models import Motorcycle
import logging

def get_motorcycle_details(pk: int):
    try:
        motorcycle = Motorcycle.objects.prefetch_related("conditions").get(pk=pk)
        return motorcycle
    except ObjectDoesNotExist:
        logging.warning(f"Motorcycle with pk {pk} not found.")
        return None
    except Exception as e:
        logging.error(f"An error occurred while retrieving motorcycle with pk {pk}: {e}")
        return None
