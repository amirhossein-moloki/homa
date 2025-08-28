from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdditionalServiceViewSet

router = DefaultRouter()
router.register(r'additional-services', AdditionalServiceViewSet, basename='additional-service')

urlpatterns = [
    path('', include(router.urls)),
]
