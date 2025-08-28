from django.contrib import admin
from .models import AdditionalService

# Unregister the model if it's already registered
if admin.site.is_registered(AdditionalService):
    admin.site.unregister(AdditionalService)

@admin.register(AdditionalService)
class AdditionalServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
