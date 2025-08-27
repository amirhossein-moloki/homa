from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Province, City
from users.models import CustomUser

class CityAPITestCase(APITestCase):
    def setUp(self):
        self.admin_user = CustomUser.objects.create_superuser(
            phone_number='09123456789',
            password='adminpassword',
            full_name='Admin User',
            email='admin@example.com'
        )
        self.user = CustomUser.objects.create_user(
            phone_number='09987654321',
            password='userpassword',
            full_name='Regular User',
            email='user@example.com'
        )
        self.province = Province.objects.create(name='تهران')
        self.city = City.objects.create(province=self.province, name='تهران')

    def test_list_provinces_unauthenticated(self):
        url = reverse('province-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_province_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('province-list')
        data = {'name': 'البرز'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Province.objects.filter(name='البرز').exists())

    def test_create_province_as_user(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('province-list')
        data = {'name': 'فارس'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_cities_unauthenticated(self):
        url = reverse('city-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_city_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('city-list')
        data = {'name': 'کرج', 'province': self.province.id}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(City.objects.filter(name='کرج').exists())

    def test_create_city_as_user(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('city-list')
        data = {'name': 'شیراز', 'province': self.province.id}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
