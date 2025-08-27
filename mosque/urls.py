from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FacilityViewSet, MosqueViewSet, HallViewSet, ImageViewSet

router = DefaultRouter()
router.register(r'facilities', FacilityViewSet)
router.register(r'mosques', MosqueViewSet)
router.register(r'halls', HallViewSet)
router.register(r'images', ImageViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
