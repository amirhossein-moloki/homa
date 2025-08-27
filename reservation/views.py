from rest_framework import viewsets, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime
from decimal import Decimal

from .models import Reservation
from .serializers import ReservationSerializer
from mosque.models import Hall, Mosque
from services.models import AdditionalService

class ReservationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user reservations.
    """
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Users can only see their own reservations.
        """
        return Reservation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        Custom logic to calculate total price and check for time conflicts before saving.
        """
        hall = serializer.validated_data['hall']
        start_time = serializer.validated_data['start_time']
        end_time = serializer.validated_data['end_time']

        # 1. Check for valid time range
        if start_time >= end_time or start_time < timezone.now():
            raise serializers.ValidationError({'error': 'Invalid time range.'})

        # 2. Check for time conflicts
        conflicting_reservations = Reservation.objects.filter(
            hall=hall,
            status=Reservation.ReservationStatus.ACTIVE,
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        if conflicting_reservations.exists():
            raise serializers.ValidationError({'error': 'This time slot is already booked.'})

        # 3. Calculate total price
        # Hall price
        duration_hours = (end_time - start_time).total_seconds() / 3600
        total_price = Decimal(str(duration_hours)) * hall.price_per_hour

        # Services price
        services_data = self.request.data.get('reservation_services', [])
        if services_data:
            service_ids = [item['service_id'] for item in services_data]
            services = AdditionalService.objects.in_bulk(service_ids)

            for item in services_data:
                service = services.get(int(item['service_id']))
                if service:
                    quantity = item.get('quantity', 1)
                    total_price += service.price * Decimal(quantity)

        # 4. Save the reservation with the calculated price
        serializer.save(user=self.request.user, total_price=total_price)


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
