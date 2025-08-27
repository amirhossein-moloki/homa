from django.db import models

class Province(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام استان")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "استان"
        verbose_name_plural = "استان‌ها"

class City(models.Model):
    province = models.ForeignKey(Province, on_delete=models.CASCADE, related_name='cities', verbose_name="استان")
    name = models.CharField(max_length=100, verbose_name="نام شهر")

    def __str__(self):
        return f"{self.name} ({self.province.name})"

    class Meta:
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"
        unique_together = ('province', 'name')
