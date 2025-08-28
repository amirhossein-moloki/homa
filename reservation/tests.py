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

# The path to patch is where the class is *looked up*, which is in the views module.
# So, we patch 'reservation.views.ZarinpalGateway'
ZARINPAL_GATEWAY_PATH = 'reservation.views.ZarinpalGateway'


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

    @patch(ZARINPAL_GATEWAY_PATH)
    def test_create_reservation_success(self, MockZarinpalGateway):
        # The mock gateway's create_payment_request should return a tuple (payment_url, authority)
        mock_gateway_instance = MockZarinpalGateway.return_value
        mock_gateway_instance.create_payment_request.return_value = ("https://sandbox.zarinpal.com/pg/TEST_AUTHORITY_123", "TEST_AUTHORITY_123")

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
        self.assertIn('This time slot is already booked.', response.data.get('non_field_errors', []))

    def test_create_reservation_invalid_time_range(self):
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time - timedelta(hours=2)
        data = {'hall_id': self.hall.id, 'start_time': start_time.isoformat(), 'end_time': end_time.isoformat()}
        response = self.client.post(self.reservations_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Convert ErrorDetail objects to strings for comparison
        errors = [str(e) for e in response.data.get('non_field_errors', [])]
        self.assertIn("End time must be after start time.", errors)

    def test_create_reservation_start_time_in_past(self):
        start_time = timezone.now() - timedelta(days=1)
        end_time = start_time + timedelta(hours=2)
        data = {'hall_id': self.hall.id, 'start_time': start_time.isoformat(), 'end_time': end_time.isoformat()}
        response = self.client.post(self.reservations_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Convert ErrorDetail objects to strings for comparison
        errors = [str(e) for e in response.data.get('non_field_errors', [])]
        self.assertIn("Reservation start time cannot be in the past.", errors)

    @patch(ZARINPAL_GATEWAY_PATH)
    def test_create_reservation_gateway_fails_rolls_back(self, MockZarinpalGateway):
        mock_gateway_instance = MockZarinpalGateway.return_value
        mock_gateway_instance.create_payment_request.side_effect = Exception("Gateway connection error")

        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)
        data = {'hall_id': self.hall.id, 'start_time': start_time.isoformat(), 'end_time': end_time.isoformat()}

        # Ensure no reservations exist before the test
        self.assertEqual(Reservation.objects.count(), 0)

        response = self.client.post(self.reservations_url, data, format='json')

        # The view should catch the exception and return a 503
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

        # The transaction should be rolled back, so no reservation should be created
        self.assertEqual(Reservation.objects.count(), 0)

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

    @patch(ZARINPAL_GATEWAY_PATH)
    def test_callback_success(self, MockZarinpalGateway):
        mock_gateway_instance = MockZarinpalGateway.return_value
        # verify_payment should return (True, ref_id) on success
        mock_gateway_instance.verify_payment.return_value = (True, "REF123")

        response = self.client.get(f"{self.callback_url}?Authority=TEST_CALLBACK_AUTH&Status=OK")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.ReservationStatus.ACTIVE)

    @patch(ZARINPAL_GATEWAY_PATH)
    def test_callback_verification_failed(self, MockZarinpalGateway):
        mock_gateway_instance = MockZarinpalGateway.return_value
        # verify_payment should return (False, error_details) on failure
        mock_gateway_instance.verify_payment.return_value = (False, {"code": -51, "message": "Invalid amount"})

        response = self.client.get(f"{self.callback_url}?Authority=TEST_CALLBACK_AUTH&Status=OK")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.ReservationStatus.FAILED)

    def test_callback_user_cancelled(self):
        response = self.client.get(f"{self.callback_url}?Authority=TEST_CALLBACK_AUTH&Status=NOK")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.ReservationStatus.FAILED)
