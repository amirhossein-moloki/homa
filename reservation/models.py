from django.db import models
from django.conf import settings
from mosque.models import Hall
from services.models import AdditionalService

class ReservationService(models.Model):
    reservation = models.ForeignKey('Reservation', on_delete=models.CASCADE, related_name='reservation_services')
    service = models.ForeignKey(AdditionalService, on_delete=models.CASCADE, related_name='reservation_services')
    quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")

    class Meta:
        verbose_name = "سرویس رزرو"
        verbose_name_plural = "سرویس‌های رزرو"
        unique_together = ('reservation', 'service')

    def __str__(self):
        return f"{self.quantity} x {self.service.name} for Reservation {self.reservation.id}"

class Reservation(models.Model):
    class ReservationStatus(models.TextChoices):
        PENDING = 'PENDING', 'در انتظار پرداخت'
        ACTIVE = 'ACTIVE', 'فعال'
        CANCELLED = 'CANCELLED', 'لغو شده'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name="کاربر"
    )
    hall = models.ForeignKey(
        Hall,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name="سالن"
    )
    start_time = models.DateTimeField(verbose_name="زمان شروع")
    end_time = models.DateTimeField(verbose_name="زمان پایان")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="مبلغ کل")
    status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PENDING,
        verbose_name="وضعیت"
    )
    services = models.ManyToManyField(
        AdditionalService,
        through='ReservationService',
        blank=True,
        verbose_name="خدمات جانبی"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    def __str__(self):
        return f"رزرو {self.id} برای سالن {self.hall.name} توسط {self.user.full_name}"

    class Meta:
        verbose_name = "رزرو"
        verbose_name_plural = "رزروها"
        ordering = ['-start_time']
