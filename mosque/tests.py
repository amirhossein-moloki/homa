from django.test import TestCase
from .models import Mosque, Hall, Facility, Image
from cities.models import Province, City

class MosqueModelTest(TestCase):
    def setUp(self):
        self.facility1 = Facility.objects.create(name="سیستم صوت")
        self.province_tehran = Province.objects.create(name="تهران")
        self.city_tehran = City.objects.create(province=self.province_tehran, name="تهران")

        self.mosque1 = Mosque.objects.create(
            name="مسجد جامع",
            city=self.city_tehran,
            address="خیابان اصلی",
            latitude=35.6892,
            longitude=51.3890
        )
        self.hall1 = Hall.objects.create(
            mosque=self.mosque1,
            name="سالن اصلی",
            capacity=200,
            price_per_hour=100000
        )

    def test_facility_creation(self):
        self.assertEqual(self.facility1.name, "سیستم صوت")

    def test_mosque_creation(self):
        self.assertEqual(self.mosque1.name, "مسجد جامع")
        self.assertEqual(self.mosque1.city.name, "تهران")
        self.assertEqual(self.mosque1.city.province.name, "تهران")

    def test_hall_creation(self):
        self.assertEqual(self.hall1.name, "سالن اصلی")
        self.assertEqual(self.hall1.mosque.name, "مسجد جامع")

    def test_add_facility_to_hall(self):
        self.hall1.facilities.add(self.facility1)
        self.assertEqual(self.hall1.facilities.count(), 1)
        self.assertEqual(self.hall1.facilities.first().name, "سیستم صوت")

    def test_image_creation_for_mosque(self):
        image = Image.objects.create(
            mosque=self.mosque1,
            image='images/test_mosque.jpg'
        )
        self.assertEqual(image.mosque, self.mosque1)

    def test_image_creation_for_hall(self):
        image = Image.objects.create(
            hall=self.hall1,
            image='images/test_hall.jpg'
        )
        self.assertEqual(image.hall, self.hall1)

    def test_model_str_methods(self):
        self.assertEqual(str(self.facility1), "سیستم صوت")
        self.assertEqual(str(self.province_tehran), "تهران")
        self.assertEqual(str(self.city_tehran), "تهران (تهران)")
        self.assertEqual(str(self.mosque1), "مسجد جامع")
        self.assertEqual(str(self.hall1), "سالن اصلی (مسجد جامع)")
        image = Image.objects.create(mosque=self.mosque1, image='images/test.jpg')
        self.assertEqual(str(image), "تصویر مسجد مسجد جامع")


from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from users.models import CustomUser

class MosqueAPITestCase(APITestCase):
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
        self.mosque = Mosque.objects.create(
            name="مسجد تست",
            city=self.city,
            address="آدرس تست",
            latitude=35.7,
            longitude=51.4
        )

    def test_list_mosques_unauthenticated(self):
        url = reverse('mosque-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_mosque_as_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('mosque-list')
        data = {
            'name': 'مسجد جدید',
            'city_id': self.city.id,
            'address': 'آدرس جدید',
            'latitude': 35.71,
            'longitude': 51.41
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Mosque.objects.filter(name='مسجد جدید').exists())

    def test_create_mosque_as_user(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('mosque-list')
        data = {
            'name': 'مسجد کاربر',
            'city_id': self.city.id,
            'address': 'آدرس کاربر',
            'latitude': 35.72,
            'longitude': 51.42
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
