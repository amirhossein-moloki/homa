from rest_framework import serializers
from .models import Reservation, AdditionalService
from users.serializers import UserSerializer
from mosque.serializers import HallSerializer

class AdditionalServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdditionalService
        fields = '__all__'

class ReservationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    hall = HallSerializer(read_only=True)
    services = AdditionalServiceSerializer(many=True, read_only=True)

    hall_id = serializers.IntegerField(write_only=True)
    service_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = Reservation
        fields = [
            'id',
            'user',
            'hall',
            'start_time',
            'end_time',
            'total_price',
            'status',
            'services',
            'created_at',
            'updated_at',
            'hall_id',
            'service_ids',
        ]
        read_only_fields = ['total_price', 'status', 'user']

    def create(self, validated_data):
        # The core logic for creation, price calculation, and conflict checking
        # will be handled in the ViewSet to keep the serializer clean.
        # The serializer's job is to validate the input data format.
        return super().create(validated_data)
