from rest_framework import viewsets
from .permissions import IsAdmin
from .serializers import (
    UserAdminSerializer,
    ProvinceAdminSerializer,
    CityAdminSerializer,
    FacilityAdminSerializer,
    MosqueAdminSerializer,
    HallAdminSerializer,
    ImageAdminSerializer,
    AdditionalServiceAdminSerializer,
    ReservationAdminSerializer,
)
from users.models import CustomUser
from cities.models import Province, City
from mosque.models import Facility, Mosque, Hall, Image
from services.models import AdditionalService
from reservation.models import Reservation

class BaseAdminViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet for admin panels.
    - Enforces Admin-only access.
    """
    permission_classes = [IsAdmin]


class UserAdminViewSet(BaseAdminViewSet):
    """Admin ViewSet for managing Users."""
    queryset = CustomUser.objects.all().order_by('-date_joined')
    serializer_class = UserAdminSerializer


class ProvinceAdminViewSet(BaseAdminViewSet):
    """Admin ViewSet for Provinces."""
    queryset = Province.objects.all()
    serializer_class = ProvinceAdminSerializer


class CityAdminViewSet(BaseAdminViewSet):
    """Admin ViewSet for Cities."""
    queryset = City.objects.select_related('province').all()
    serializer_class = CityAdminSerializer


class FacilityAdminViewSet(BaseAdminViewSet):
    """Admin ViewSet for Facilities."""
    queryset = Facility.objects.all()
    serializer_class = FacilityAdminSerializer


class MosqueAdminViewSet(BaseAdminViewSet):
    """Admin ViewSet for Mosques."""
    queryset = Mosque.objects.prefetch_related('halls', 'images').select_related('city').all()
    serializer_class = MosqueAdminSerializer


class HallAdminViewSet(BaseAdminViewSet):
    """Admin ViewSet for Halls."""
    queryset = Hall.objects.prefetch_related('facilities', 'images').select_related('mosque').all()
    serializer_class = HallAdminSerializer


class ImageAdminViewSet(BaseAdminViewSet):
    """Admin ViewSet for Images."""
    queryset = Image.objects.all()
    serializer_class = ImageAdminSerializer


class AdditionalServiceAdminViewSet(BaseAdminViewSet):
    """Admin ViewSet for Additional Services."""
    queryset = AdditionalService.objects.all()
    serializer_class = AdditionalServiceAdminSerializer


class ReservationAdminViewSet(BaseAdminViewSet):
    """Admin ViewSet for Reservations."""
    queryset = Reservation.objects.select_related('user', 'hall').prefetch_related('reservation_services__service').all().order_by('-created_at')
    serializer_class = ReservationAdminSerializer
