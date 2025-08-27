from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.utils import timezone
from datetime import timedelta, datetime
from unittest.mock import patch
from decimal import Decimal

from users.models import CustomUser
from mosque.models import Mosque, Hall, City
from .models import Reservation, ReservationService
from services.models import AdditionalService
from cities.models import Province

class ReservationAPITests(APITestCase):
    def setUp(self):
        self.province = Province.objects.create(name="Test Province")
        self.city = City.objects.create(name="Test City", province=self.province)
        self.user = CustomUser.objects.create_user(
            phone_number='1234567890',
            password='testpassword123',
            full_name='Test User',
            email='test@example.com'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.mosque = Mosque.objects.create(
            name="Test Mosque",
            city=self.city,
            address="123 Test St",
            latitude=0.0,
            longitude=0.0
        )
        self.hall = Hall.objects.create(mosque=self.mosque, name="Main Hall", capacity=100, price_per_hour=50.00)
        self.service1 = AdditionalService.objects.create(name="Flowers", price=20.00, is_active=True)
        self.service2 = AdditionalService.objects.create(name="Sound System", price=30.00, is_active=True)
        self.inactive_service = AdditionalService.objects.create(name="Inactive Service", price=10.00, is_active=False)
        self.reservations_url = reverse('reservation-list')
        self.availability_url = reverse('mosque-availability', kwargs={'mosque_id': self.mosque.id})

    def test_create_reservation_unauthenticated(self):
        self.client.logout()
        response = self.client.post(self.reservations_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('reservation.views.ZarinPal')
    def test_create_reservation_success(self, MockZarinPal):
        mock_zarinpal_instance = MockZarinPal.return_value
        mock_zarinpal_instance.payments.create.return_value = {"data": {"authority": "TEST_AUTHORITY_123"}, "errors": []}
        mock_zarinpal_instance.payments.generate_payment_url.return_value = "https://sandbox.zarinpal.com/pg/TEST_AUTHORITY_123"

        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)
        data = {
            'hall_id': self.hall.id,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'reservation_services': [{'service_id': self.service1.id, 'quantity': 2}, {'service_id': self.service2.id, 'quantity': 1}]
        }
        response = self.client.post(self.reservations_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('payment_url', response.data)

        self.assertEqual(Reservation.objects.count(), 1)
        reservation = Reservation.objects.first()
        self.assertEqual(reservation.authority, "TEST_AUTHORITY_123")
        self.assertEqual(reservation.total_price, Decimal('170.00'))

    def test_create_reservation_with_inactive_service(self):
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)
        data = {
            'hall_id': self.hall.id,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'reservation_services': [{'service_id': self.inactive_service.id, 'quantity': 1}]
        }
        response = self.client.post(self.reservations_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_reservation_time_conflict(self):
        start_time1 = timezone.now() + timedelta(days=2, hours=1)
        end_time1 = start_time1 + timedelta(hours=3)
        Reservation.objects.create(
            user=self.user, hall=self.hall, start_time=start_time1, end_time=end_time1,
            total_price=150.00, status=Reservation.ReservationStatus.ACTIVE
        )

        start_time2 = start_time1 + timedelta(hours=1)
        end_time2 = start_time2 + timedelta(hours=2)
        data = {'hall_id': self.hall.id, 'start_time': start_time2.isoformat(), 'end_time': end_time2.isoformat()}
        response = self.client.post(self.reservations_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0], 'This time slot is already booked.')

    def test_create_reservation_invalid_time_range(self):
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time - timedelta(hours=2)
        data = {'hall_id': self.hall.id, 'start_time': start_time.isoformat(), 'end_time': end_time.isoformat()}
        response = self.client.post(self.reservations_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0], 'Invalid time range.')

    def test_get_mosque_availability(self):
        target_date = timezone.now().date() + timedelta(days=5)
        start_time = timezone.make_aware(datetime.combine(target_date, datetime.min.time()) + timedelta(hours=10))
        end_time = start_time + timedelta(hours=4)
        Reservation.objects.create(
            user=self.user, hall=self.hall, start_time=start_time, end_time=end_time,
            total_price=200.00, status=Reservation.ReservationStatus.ACTIVE
        )

        response = self.client.get(self.availability_url, {'date': target_date.strftime('%Y-%m-%d')})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data[0]['booked_slots']), 1)


class PaymentCallbackTests(APITestCase):
    def setUp(self):
        self.province = Province.objects.create(name="Test Province")
        self.city = City.objects.create(name="Test City", province=self.province)
        self.user = CustomUser.objects.create_user(phone_number='0987654321', password='testpassword123', full_name='Test User 2', email='test2@example.com')
        self.mosque = Mosque.objects.create(
            name="Test Mosque 2", city=self.city, address="456 Test St", latitude=0.0, longitude=0.0
        )
        self.hall = Hall.objects.create(mosque=self.mosque, name="Side Hall", capacity=50, price_per_hour=25.00)
        self.reservation = Reservation.objects.create(
            user=self.user, hall=self.hall, start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, hours=2), total_price=50.00,
            status=Reservation.ReservationStatus.PENDING, authority="TEST_CALLBACK_AUTH"
        )
        self.callback_url = reverse('payment-callback')

    @patch('reservation.views.ZarinPal')
    def test_callback_success(self, MockZarinPal):
        mock_zarinpal_instance = MockZarinPal.return_value
        mock_zarinpal_instance.verifications.verify.return_value = {"data": {"code": 100, "ref_id": "REF123"}, "errors": []}

        response = self.client.get(f"{self.callback_url}?Authority=TEST_CALLBACK_AUTH&Status=OK")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.ReservationStatus.ACTIVE)

    @patch('reservation.views.ZarinPal')
    def test_callback_verification_failed(self, MockZarinPal):
        mock_zarinpal_instance = MockZarinPal.return_value
        mock_zarinpal_instance.verifications.verify.return_value = {"data": {"code": -51}, "errors": ["Invalid amount"]}

        response = self.client.get(f"{self.callback_url}?Authority=TEST_CALLBACK_AUTH&Status=OK")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.ReservationStatus.FAILED)

    def test_callback_user_cancelled(self):
        response = self.client.get(f"{self.callback_url}?Authority=TEST_CALLBACK_AUTH&Status=NOK")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.ReservationStatus.FAILED)
