from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# A router is used to automatically generate the URL patterns for a ViewSet.
router = DefaultRouter()

# Register each ViewSet with the router.
# The `basename` is important for reverse URL lookups.
router.register(r'users', views.UserAdminViewSet, basename='admin-user')
router.register(r'provinces', views.ProvinceAdminViewSet, basename='admin-province')
router.register(r'cities', views.CityAdminViewSet, basename='admin-city')
router.register(r'facilities', views.FacilityAdminViewSet, basename='admin-facility')
router.register(r'mosques', views.MosqueAdminViewSet, basename='admin-mosque')
router.register(r'halls', views.HallAdminViewSet, basename='admin-hall')
router.register(r'images', views.ImageAdminViewSet, basename='admin-image')
router.register(r'services', views.AdditionalServiceAdminViewSet, basename='admin-service')
router.register(r'reservations', views.ReservationAdminViewSet, basename='admin-reservation')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
]
