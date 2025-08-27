from rest_framework import viewsets, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from django.urls import reverse
from django.conf import settings
from django.shortcuts import get_object_or_404

from .models import Reservation, ReservationService
from .serializers import ReservationSerializer
from mosque.models import Hall, Mosque
from services.models import AdditionalService
from zarinpal import ZarinPal
from .config import Config


class ReservationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user reservations.
    Integrates with Zarinpal payment gateway.
    """
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Users can only see their own reservations.
        """
        return Reservation.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        hall = validated_data['hall']
        start_time = validated_data['start_time']
        end_time = validated_data['end_time']

        # 1. Custom Validation
        if start_time >= end_time or start_time < timezone.now():
            raise serializers.ValidationError("Invalid time range.")

        conflicting_reservations = Reservation.objects.filter(
            hall=hall,
            status=Reservation.ReservationStatus.ACTIVE,
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        if conflicting_reservations.exists():
            raise serializers.ValidationError("This time slot is already booked.")

        # 2. Calculate total price
        duration_hours = (end_time - start_time).total_seconds() / 3600
        total_price = Decimal(str(duration_hours)) * hall.price_per_hour

        services_data = validated_data.pop('reservation_services', [])
        for service_item in services_data:
            service = service_item['service']
            quantity = service_item['quantity']
            total_price += service.price * Decimal(quantity)

        # 3. Manually create the reservation and related services
        reservation = Reservation.objects.create(
            user=request.user,
            total_price=total_price,
            **validated_data
        )
        for service_item in services_data:
            ReservationService.objects.create(
                reservation=reservation,
                service=service_item['service'],
                quantity=service_item['quantity']
            )

        # 4. Zarinpal Payment Integration
        merchant_id = getattr(settings, 'ZARINPAL_MERCHANT_ID', 'YOUR_MERCHANT_ID')
        config = Config(merchant_id=merchant_id, sandbox=True)
        zarinpal = ZarinPal(config)

        amount = int(reservation.total_price)
        if amount < 10000:
            amount = 10000

        callback_url = request.build_absolute_uri(reverse('payment-callback'))
        payment_data = {
            "amount": amount,
            "callback_url": callback_url,
            "description": f"Reservation for {reservation.hall.name} - ID: {reservation.id}",
            "email": getattr(reservation.user, 'email', ''),
            "mobile": getattr(reservation.user, 'phone_number', ''),
        }

        try:
            res = zarinpal.payments.create(payment_data)
        except Exception as e:
            reservation.status = Reservation.ReservationStatus.FAILED
            reservation.save()
            return Response(
                {"error": "Payment gateway connection error.", "details": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        if res.get("data") and res.get("data", {}).get("authority"):
            authority = res["data"]["authority"]
            reservation.authority = authority
            reservation.save()
            payment_url = zarinpal.payments.generate_payment_url(authority)
            return Response({'payment_url': payment_url, 'reservation_id': reservation.id}, status=status.HTTP_201_CREATED)
        else:
            reservation.status = Reservation.ReservationStatus.FAILED
            reservation.save()
            error_details = res.get("errors", "Unknown error from payment gateway.")
            return Response(
                {"error": "Could not get payment authority.", "details": error_details},
                status=status.HTTP_400_BAD_REQUEST
            )


class MosqueAvailabilityAPIView(APIView):
    """
    API view to get the availability of halls in a mosque for a specific date.
    """
    def get(self, request, mosque_id, *args, **kwargs):
        try:
            date_str = request.query_params.get('date', timezone.now().strftime('%Y-%m-%d'))
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            mosque = Mosque.objects.get(id=mosque_id)
        except Mosque.DoesNotExist:
            return Response({'error': 'Mosque not found.'}, status=status.HTTP_404_NOT_FOUND)

        halls = mosque.halls.all()
        availability_data = []

        for hall in halls:
            booked_slots_qs = Reservation.objects.filter(
                hall=hall,
                status=Reservation.ReservationStatus.ACTIVE,
                start_time__date=target_date
            )

            booked_slots_data = [
                {
                    "start_time": res.start_time.isoformat(),
                    "end_time": res.end_time.isoformat()
                }
                for res in booked_slots_qs
            ]

            availability_data.append({
                'hall_id': hall.id,
                'hall_name': hall.name,
                'booked_slots': booked_slots_data
            })

        return Response(availability_data, status=status.HTTP_200_OK)


class PaymentCallbackView(APIView):
    """
    Handles the callback from Zarinpal after a payment attempt.
    """
    permission_classes = [] # This view must be public for Zarinpal to access

    def get(self, request, *args, **kwargs):
        authority = request.query_params.get('Authority')
        status_param = request.query_params.get('Status')

        if not authority or not status_param:
            return Response(
                {"error": "Invalid callback parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )

        reservation = get_object_or_404(Reservation, authority=authority)

        if reservation.status != Reservation.ReservationStatus.PENDING:
            return Response(
                {"message": f"Reservation status is already '{reservation.status}'. No action taken."},
                status=status.HTTP_200_OK
            )

        if status_param == 'OK':
            merchant_id = getattr(settings, 'ZARINPAL_MERCHANT_ID', 'YOUR_MERCHANT_ID')
            config = Config(merchant_id=merchant_id, sandbox=True)
            zarinpal = ZarinPal(config)

            amount = int(reservation.total_price)
            if amount < 10000:
                amount = 10000

            verification_data = {
                "amount": amount,
                "authority": authority,
            }

            try:
                res = zarinpal.verifications.verify(verification_data)
            except Exception as e:
                 reservation.status = Reservation.ReservationStatus.FAILED
                 reservation.save()
                 return Response(
                    {"error": "Payment verification failed during communication with the gateway.", "details": str(e)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            if res.get("data") and res["data"].get("code") == 100:
                reservation.status = Reservation.ReservationStatus.ACTIVE
                reservation.save()
                return Response(
                    {"message": "Payment successful and reservation is now active.", "ref_id": res["data"]["ref_id"]},
                    status=status.HTTP_200_OK
                )
            elif res.get("data") and res["data"].get("code") == 101:
                if reservation.status == Reservation.ReservationStatus.PENDING:
                    reservation.status = Reservation.ReservationStatus.ACTIVE
                    reservation.save()
                return Response(
                    {"message": "Payment was already verified."},
                    status=status.HTTP_200_OK
                )
            else:
                reservation.status = Reservation.ReservationStatus.FAILED
                reservation.save()
                error_details = res.get("errors") or res.get("data")
                return Response(
                    {"error": "Payment verification failed.", "details": error_details},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            reservation.status = Reservation.ReservationStatus.FAILED
            reservation.save()
            return Response(
                {"error": "Payment was cancelled by the user."},
                status=status.HTTP_400_BAD_REQUEST
            )
