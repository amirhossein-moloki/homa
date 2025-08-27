from rest_framework import serializers
from users.models import CustomUser
from cities.models import Province, City
from mosque.models import Facility, Mosque, Hall, Image
from services.models import AdditionalService
from reservation.models import Reservation, ReservationService

class UserAdminSerializer(serializers.ModelSerializer):
    """
    Serializer for the CustomUser model for the admin panel.
    Handles password hashing on user creation and updates.
    """
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})

    class Meta:
        model = CustomUser
        fields = (
            'id', 'phone_number', 'email', 'full_name', 'national_id',
            'role', 'is_active', 'is_staff', 'is_verified', 'password',
            'date_joined', 'last_updated'
        )
        read_only_fields = ('date_joined', 'last_updated')

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        return super().update(instance, validated_data)


class ProvinceAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = '__all__'


class CityAdminSerializer(serializers.ModelSerializer):
    province_name = serializers.CharField(source='province.name', read_only=True)

    class Meta:
        model = City
        fields = ('id', 'name', 'province', 'province_name')


class FacilityAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = '__all__'


class ImageAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = '__all__'


class HallAdminSerializer(serializers.ModelSerializer):
    mosque_name = serializers.CharField(source='mosque.name', read_only=True)
    # Use PrimaryKeyRelatedField for writing to the m2m relationship
    facilities = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Facility.objects.all(), write_only=True, required=False
    )
    # Use a separate serializer for reading to show facility details
    facilities_details = FacilityAdminSerializer(source='facilities', many=True, read_only=True)

    class Meta:
        model = Hall
        fields = (
            'id', 'name', 'capacity', 'price_per_hour', 'mosque', 'mosque_name',
            'facilities', 'facilities_details'
        )

class MosqueAdminSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    halls = HallAdminSerializer(many=True, read_only=True)
    images = ImageAdminSerializer(many=True, read_only=True)

    class Meta:
        model = Mosque
        fields = (
            'id', 'name', 'address', 'latitude', 'longitude', 'description',
            'city', 'city_name', 'halls', 'images'
        )


class AdditionalServiceAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdditionalService
        fields = '__all__'


class ReservationServiceAdminSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = ReservationService
        fields = ('id', 'service', 'service_name', 'quantity')


class ReservationAdminSerializer(serializers.ModelSerializer):
    user_details = serializers.StringRelatedField(source='user', read_only=True)
    hall_details = serializers.StringRelatedField(source='hall', read_only=True)

    # For displaying services with quantity
    reservation_services = ReservationServiceAdminSerializer(many=True, read_only=True)

    # For adding/updating services
    services = serializers.PrimaryKeyRelatedField(
        many=True, queryset=AdditionalService.objects.all(), write_only=True, required=False
    )

    class Meta:
        model = Reservation
        fields = (
            'id', 'user', 'user_details', 'hall', 'hall_details', 'start_time', 'end_time',
            'total_price', 'status', 'authority', 'created_at', 'updated_at',
            'services', 'reservation_services'
        )
        read_only_fields = ('created_at', 'updated_at', 'total_price', 'authority')

    def create(self, validated_data):
        services_data = validated_data.pop('services', [])
        reservation = Reservation.objects.create(**validated_data)
        # Note: This simple approach doesn't create ReservationService with quantity.
        # A more complex implementation would handle a nested list of service IDs and quantities.
        # For now, we just associate the services.
        reservation.services.set(services_data)
        return reservation

    def update(self, instance, validated_data):
        services_data = validated_data.pop('services', None)
        if services_data is not None:
            instance.services.set(services_data)

        return super().update(instance, validated_data)
