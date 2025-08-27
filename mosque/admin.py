from django.contrib import admin
from .models import Mosque, Hall, Image, Facility

class ImageInline(admin.TabularInline):
    model = Image
    extra = 1

class HallInline(admin.TabularInline):
    model = Hall
    extra = 1

@admin.register(Mosque)
class MosqueAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'get_province')
    list_filter = ('city__province', 'city')
    search_fields = ('name', 'address', 'city__name', 'city__province__name')
    inlines = [HallInline, ImageInline]

    def get_province(self, obj):
        return obj.city.province
    get_province.short_description = 'استان'
    get_province.admin_order_field = 'city__province'


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ('name', 'mosque', 'capacity', 'price_per_hour')
    list_filter = ('mosque__city__province', 'mosque__city')
    search_fields = ('name', 'mosque__name')
    inlines = [ImageInline]

@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'mosque', 'hall')
    list_filter = ('mosque', 'hall')
