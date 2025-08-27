from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.utils import timezone
from datetime import timedelta

from users.models import CustomUser
from mosque.models import Mosque, Hall, City
from .models import Reservation, AdditionalService
from cities.models import Province

class ReservationAPITests(APITestCase):
    def setUp(self):
        # Create a province and a city
        self.province = Province.objects.create(name="Test Province")
        self.city = City.objects.create(name="Test City", province=self.province)

        # Create a user
        self.user = CustomUser.objects.create_user(
            phone_number='1234567890',
            password='testpassword123',
            full_name='Test User'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create a mosque and a hall
        self.mosque = Mosque.objects.create(
            name="Test Mosque",
            city=self.city,
            address="123 Test St",
            latitude=0.0,
            longitude=0.0
        )
        self.hall = Hall.objects.create(
            mosque=self.mosque,
            name="Main Hall",
            capacity=100,
            price_per_hour=50.00
        )

        # Create additional services
        self.service1 = AdditionalService.objects.create(name="Flowers", price=20.00)
        self.service2 = AdditionalService.objects.create(name="Sound System", price=30.00)

        # URLS
        self.reservations_url = reverse('reservation-list')
        self.availability_url = reverse('mosque-availability', kwargs={'mosque_id': self.mosque.id})

    def test_create_reservation_unauthenticated(self):
        self.client.logout()
        response = self.client.post(self.reservations_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_reservation_success(self):
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)

        data = {
            'hall_id': self.hall.id,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'service_ids': [self.service1.id]
        }
        response = self.client.post(self.reservations_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 1)

        reservation = Reservation.objects.first()
        self.assertEqual(reservation.user, self.user)
        self.assertEqual(reservation.hall, self.hall)
        # Price: 2 hours * 50/hour + 20 (service1) = 120
        self.assertEqual(reservation.total_price, 120.00)

    def test_create_reservation_time_conflict(self):
        # Create an existing active reservation
        start_time1 = timezone.now() + timedelta(days=2, hours=1)
        end_time1 = start_time1 + timedelta(hours=3)
        Reservation.objects.create(
            user=self.user,
            hall=self.hall,
            start_time=start_time1,
            end_time=end_time1,
            total_price=150.00,
            status=Reservation.ReservationStatus.ACTIVE
        )

        # Attempt to create an overlapping reservation
        start_time2 = start_time1 + timedelta(hours=1)
        end_time2 = start_time2 + timedelta(hours=2)
        data = {
            'hall_id': self.hall.id,
            'start_time': start_time2.isoformat(),
            'end_time': end_time2.isoformat(),
        }
        response = self.client.post(self.reservations_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['error'], 'This time slot is already booked.')

    def test_create_reservation_invalid_time_range(self):
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time - timedelta(hours=2) # End time is before start time

        data = {
            'hall_id': self.hall.id,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
        }
        response = self.client.post(self.reservations_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid time range.')

    def test_get_mosque_availability(self):
        # Create an active reservation for the target date
        target_date = timezone.now().date() + timedelta(days=5)
        start_time = timezone.make_aware(
            timezone.datetime.combine(target_date, timezone.datetime.min.time()) + timedelta(hours=10)
        )
        end_time = start_time + timedelta(hours=4)
        Reservation.objects.create(
            user=self.user,
            hall=self.hall,
            start_time=start_time,
            end_time=end_time,
            total_price=200.00,
            status=Reservation.ReservationStatus.ACTIVE
        )

        response = self.client.get(self.availability_url, {'date': target_date.strftime('%Y-%m-%d')})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        hall_data = response.data[0]
        self.assertEqual(hall_data['hall_id'], self.hall.id)
        self.assertEqual(len(hall_data['booked_slots']), 1)
        self.assertEqual(hall_data['booked_slots'][0]['start_time'], start_time.isoformat())
