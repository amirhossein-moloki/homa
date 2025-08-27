from rest_framework import serializers
import jdatetime
from django.utils import timezone
import datetime

class JalaliDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        if value is None:
            return None

        # Convert to local time before converting to Jalali
        value = timezone.localtime(value)
        j_date = jdatetime.datetime.fromgregorian(
            day=value.day,
            month=value.month,
            year=value.year,
            hour=value.hour,
            minute=value.minute,
            second=value.second
        )
        return j_date.strftime('%Y/%m/%d %H:%M:%S')

    def to_internal_value(self, value):
        try:
            # First, let the parent class handle initial parsing
            # This will handle ISO 8601 format from the frontend
            native_value = super().to_internal_value(value)
            return native_value
        except (serializers.ValidationError, ValueError):
            # If the default parsing fails, try to parse the Jalali format
            try:
                j_date = jdatetime.datetime.strptime(value, '%Y/%m/%d %H:%M:%S')
                g_date = j_date.togregorian()
                # Make the datetime object timezone-aware
                return timezone.make_aware(g_date, timezone.get_current_timezone())
            except ValueError:
                raise serializers.ValidationError("Date has wrong format. Use one of these formats instead: YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z] or YYYY/MM/DD HH:MM:SS.")
