from rest_framework import serializers
from .models import Mosque, Hall, Image, Facility
from cities.serializers import CitySerializer


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ["id", "image", "description"]


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ["id", "name", "description"]


class HallSerializer(serializers.ModelSerializer):
    facilities = FacilitySerializer(many=True, read_only=True)
    images = ImageSerializer(many=True, read_only=True)

    class Meta:
        model = Hall
        fields = [
            "id",
            "name",
            "capacity",
            "price_per_hour",
            "facilities",
            "images",
        ]


class MosqueSerializer(serializers.ModelSerializer):
    halls = HallSerializer(many=True, read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    city = CitySerializer(read_only=True)
    city_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Mosque
        fields = [
            "id",
            "name",
            "address",
            "latitude",
            "longitude",
            "description",
            "city",
            "city_id",
            "halls",
            "images",
        ]
