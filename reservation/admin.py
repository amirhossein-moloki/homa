from django.contrib import admin
from .models import Reservation, AdditionalService

@admin.register(AdditionalService)
class AdditionalServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    search_fields = ('name',)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'hall', 'start_time', 'end_time', 'status', 'total_price')
    list_filter = ('status', 'hall__mosque', 'hall')
    search_fields = ('user__full_name', 'user__phone_number', 'hall__name')
    raw_id_fields = ('user', 'hall')
    date_hierarchy = 'start_time'
    ordering = ('-start_time',)
