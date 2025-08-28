from rest_framework import viewsets
from .models import AdditionalService
from .serializers import AdditionalServiceSerializer

class AdditionalServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A viewset for viewing additional services.
    """
    queryset = AdditionalService.objects.filter(is_active=True)
    serializer_class = AdditionalServiceSerializer
