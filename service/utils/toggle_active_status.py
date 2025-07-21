from django.shortcuts import get_object_or_404

def toggle_active_status(model, pk):
    instance = get_object_or_404(model, pk=pk)
    instance.is_active = not instance.is_active
    instance.save()
    return instance
