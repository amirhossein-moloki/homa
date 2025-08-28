from django.utils import timezone
from rest_framework import serializers
from .models import Reservation, ReservationService
from users.serializers import UserSerializer
from mosque.serializers import HallSerializer
from mosque.models import Hall
from services.serializers import AdditionalServiceSerializer
from services.models import AdditionalService
from core.serializers import JalaliDateTimeField

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
    start_time = JalaliDateTimeField()
    end_time = JalaliDateTimeField()
    created_at = JalaliDateTimeField(read_only=True)
    updated_at = JalaliDateTimeField(read_only=True)


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

    def validate(self, attrs):
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        hall = attrs.get('hall')

        # This logic is primarily for creation. `hall`, `start_time`, and `end_time` are required.
        if not all([hall, start_time, end_time]):
            # This will likely be caught by field-level validation, but it's a safeguard.
            return attrs

        if start_time >= end_time:
            raise serializers.ValidationError("End time must be after start time.")

        # For new reservations, check if the start time is in the past.
        # For updates, this check might not be desired, but we'll keep it for now.
        if start_time < timezone.now():
            raise serializers.ValidationError("Reservation start time cannot be in the past.")

        # Check for booking conflicts
        conflicting_reservations = Reservation.objects.filter(
            hall=hall,
            status=Reservation.ReservationStatus.ACTIVE,
            start_time__lt=end_time,
            end_time__gt=start_time
        )

        # If updating an existing reservation, exclude it from the conflict check.
        if self.instance:
            conflicting_reservations = conflicting_reservations.exclude(pk=self.instance.pk)

        if conflicting_reservations.exists():
            raise serializers.ValidationError("This time slot is already booked.")

        return attrs

    def create(self, validated_data):
        services_data = validated_data.pop('reservation_services', []) # Use default empty list
        # The view will calculate the price and add the user
        reservation = Reservation.objects.create(**validated_data)
        for service_data in services_data:
            ReservationService.objects.create(reservation=reservation, **service_data)
        return reservation
