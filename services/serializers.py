from rest_framework import serializers
from .models import AdditionalService

class AdditionalServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdditionalService
        fields = ['id', 'name', 'description', 'price', 'is_active']
