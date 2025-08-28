from rest_framework import viewsets, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
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
from .payment import ZarinpalGateway


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
        Optimized with select_related and prefetch_related to prevent N+1 queries.
        """
        return Reservation.objects.filter(user=self.request.user).select_related(
            "user", "hall"
        ).prefetch_related("reservation_services__service")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        try:
            with transaction.atomic():
                hall = validated_data['hall']
                start_time = validated_data['start_time']
                end_time = validated_data['end_time']

                # 1. Validation is handled in the serializer.

                # 2. Calculate total price
                duration_hours = (end_time - start_time).total_seconds() / 3600
                total_price = Decimal(str(duration_hours)) * hall.price_per_hour

                services_data = validated_data.pop('reservation_services', [])
                for service_item in services_data:
                    service = service_item['service']
                    quantity = service_item['quantity']
                    total_price += service.price * Decimal(quantity)

                # 3. Create reservation and related services
                # Pop hall_id as it's not a field in Reservation model directly
                validated_data.pop('hall_id', None)
                reservation = Reservation.objects.create(
                    user=request.user,
                    total_price=total_price,
                    hall=hall,
                    start_time=start_time,
                    end_time=end_time
                )
                for service_item in services_data:
                    ReservationService.objects.create(
                        reservation=reservation,
                        service=service_item['service'],
                        quantity=service_item['quantity']
                    )

                # 4. Zarinpal Payment Integration using the gateway
                gateway = ZarinpalGateway(request=request)
                payment_url, authority = gateway.create_payment_request(reservation)

                reservation.authority = authority
                reservation.save()

                # The transaction will commit here upon successful exit of the `with` block
                return Response(
                    {'payment_url': payment_url, 'reservation_id': reservation.id},
                    status=status.HTTP_201_CREATED
                )
        except Exception as e:
            # This will catch both connection errors to Zarinpal and the validation error raised above
            # The transaction is automatically rolled back on any exception
            if isinstance(e, serializers.ValidationError):
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

            return Response(
                {"error": "An unexpected error occurred.", "details": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
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
            gateway = ZarinpalGateway()
            try:
                is_successful, details = gateway.verify_payment(reservation, authority)
                if is_successful:
                    reservation.status = Reservation.ReservationStatus.ACTIVE
                    reservation.save()
                    return Response(
                        {"message": "Payment successful and reservation is now active.", "ref_id": details},
                        status=status.HTTP_200_OK
                    )
                else:
                    reservation.status = Reservation.ReservationStatus.FAILED
                    reservation.save()
                    return Response(
                        {"error": "Payment verification failed.", "details": details},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Exception as e:
                # In case of communication error with Zarinpal during verification
                reservation.status = Reservation.ReservationStatus.FAILED
                reservation.save()
                return Response(
                   {"error": "Payment verification failed during communication with the gateway.", "details": str(e)},
                   status=status.HTTP_503_SERVICE_UNAVAILABLE
               )
        else:
            reservation.status = Reservation.ReservationStatus.FAILED
            reservation.save()
            return Response(
                {"error": "Payment was cancelled by the user."},
                status=status.HTTP_400_BAD_REQUEST
            )
