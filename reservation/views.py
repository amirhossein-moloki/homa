from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .models import Reservation, AdditionalService
from .serializers import ReservationSerializer
from mosque.models import Hall, Mosque

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

    def create(self, request, *args, **kwargs):
        """
        Creates a new reservation after checking for time conflicts and calculating the total price.
        """
        hall_id = request.data.get('hall_id')
        start_time_str = request.data.get('start_time')
        end_time_str = request.data.get('end_time')
        service_ids = request.data.get('service_ids', [])

        if not all([hall_id, start_time_str, end_time_str]):
            return Response({'error': 'hall_id, start_time, and end_time are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            hall = Hall.objects.get(id=hall_id)
            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.fromisoformat(end_time_str)
        except (Hall.DoesNotExist, ValueError) as e:
            return Response({'error': f'Invalid input: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        if start_time >= end_time or start_time < timezone.now():
            return Response({'error': 'Invalid time range.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check for time conflicts
        conflicting_reservations = Reservation.objects.filter(
            hall=hall,
            status=Reservation.ReservationStatus.ACTIVE,
            start_time__lt=end_time,
            end_time__gt=start_time
        )

        if conflicting_reservations.exists():
            return Response({'error': 'This time slot is already booked.'}, status=status.HTTP_409_CONFLICT)

        # Calculate total price
        try:
            duration_hours = (end_time - start_time).total_seconds() / 3600
            total_price = Decimal(str(duration_hours)) * hall.price_per_hour
        except InvalidOperation:
            return Response({'error': 'Error in price calculation.'}, status=status.HTTP_400_BAD_REQUEST)


        services = AdditionalService.objects.filter(id__in=service_ids)
        for service in services:
            total_price += service.price

        # Create reservation
        reservation = Reservation.objects.create(
            user=request.user,
            hall=hall,
            start_time=start_time,
            end_time=end_time,
            total_price=total_price
        )
        reservation.services.set(services)

        serializer = self.get_serializer(reservation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
