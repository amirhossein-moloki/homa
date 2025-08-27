from rest_framework import serializers
from .models import Reservation, ReservationService
from users.serializers import UserSerializer
from mosque.serializers import HallSerializer
from mosque.models import Hall
from services.serializers import AdditionalServiceSerializer
from services.models import AdditionalService

class ReservationServiceSerializer(serializers.ModelSerializer):
    service = AdditionalServiceSerializer(read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=AdditionalService.objects.filter(is_active=True), source='service', write_only=True
    )

    class Meta:
        model = ReservationService
        fields = ['service', 'service_id', 'quantity']

class ReservationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    hall = HallSerializer(read_only=True)
    reservation_services = ReservationServiceSerializer(many=True, required=False)

    hall_id = serializers.PrimaryKeyRelatedField(
        queryset=Hall.objects.all(), source='hall', write_only=True
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
            'reservation_services',
            'created_at',
            'updated_at',
            'hall_id',
        ]
        read_only_fields = ['status', 'user', 'total_price']

    def create(self, validated_data):
        services_data = validated_data.pop('reservation_services')
        reservation = Reservation.objects.create(**validated_data)
        for service_data in services_data:
            ReservationService.objects.create(reservation=reservation, **service_data)
        return reservation
