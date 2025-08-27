from django.db import models
from cities.models import City

class Facility(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام امکانات")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "امکانات"
        verbose_name_plural = "امکانات"

class Mosque(models.Model):
    name = models.CharField(max_length=255, verbose_name="نام مسجد")
    city = models.ForeignKey(City, on_delete=models.PROTECT, verbose_name="شهر")
    address = models.TextField(verbose_name="آدرس دقیق")
    latitude = models.FloatField(verbose_name="عرض جغرافیایی")
    longitude = models.FloatField(verbose_name="طول جغرافیایی")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "مسجد"
        verbose_name_plural = "مساجد"

class Hall(models.Model):
    mosque = models.ForeignKey(Mosque, on_delete=models.CASCADE, related_name='halls', verbose_name="مسجد")
    name = models.CharField(max_length=255, verbose_name="نام سالن")
    capacity = models.PositiveIntegerField(verbose_name="ظرفیت")
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قیمت به ازای هر ساعت")
    facilities = models.ManyToManyField(Facility, blank=True, verbose_name="امکانات")


    def __str__(self):
        return f"{self.name} ({self.mosque.name})"

    class Meta:
        verbose_name = "سالن"
        verbose_name_plural = "سالن‌ها"

class Image(models.Model):
    mosque = models.ForeignKey(Mosque, on_delete=models.CASCADE, related_name='images', null=True, blank=True, verbose_name="مسجد")
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='images', null=True, blank=True, verbose_name="سالن")
    image = models.ImageField(upload_to='images/', verbose_name="تصویر")
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name="توضیحات تصویر")

    def __str__(self):
        if self.mosque:
            return f"تصویر مسجد {self.mosque.name}"
        elif self.hall:
            return f"تصویر سالن {self.hall.name}"
        return "تصویر بدون مرجع"

    class Meta:
        verbose_name = "تصویر"
        verbose_name_plural = "تصاویر"
