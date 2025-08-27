from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReservationViewSet, MosqueAvailabilityAPIView

router = DefaultRouter()
router.register(r'reservations', ReservationViewSet, basename='reservation')

urlpatterns = [
    path('', include(router.urls)),
    path('mosques/<int:mosque_id>/availability/', MosqueAvailabilityAPIView.as_view(), name='mosque-availability'),
]
