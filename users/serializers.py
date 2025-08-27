from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import serializers
from .models import CustomUser
from core.serializers import JalaliDateTimeField

class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = CustomUser
        fields = ('id', 'phone_number', 'email', 'full_name', 'password')

class UserSerializer(BaseUserSerializer):
    date_joined = JalaliDateTimeField(read_only=True)

    class Meta(BaseUserSerializer.Meta):
        model = CustomUser
        fields = ('id', 'phone_number', 'email', 'full_name', 'role', 'national_id', 'is_verified', 'date_joined')
