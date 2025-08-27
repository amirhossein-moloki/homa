from django.contrib import admin
from .models import Province, City

class CityInline(admin.TabularInline):
    model = City
    extra = 1

@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [CityInline]

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'province')
    list_filter = ('province',)
    search_fields = ('name', 'province__name')
