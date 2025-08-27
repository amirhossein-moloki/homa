from django.db import models

class AdditionalService(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام خدمت")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قیمت")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "خدمت جانبی"
        verbose_name_plural = "خدمات جانبی"
