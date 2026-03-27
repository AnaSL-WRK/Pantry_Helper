from django.contrib import admin
from .models import Category, Household, HouseholdMember, Item

# Register your models here.

admin.site.register(Household)
admin.site.register(HouseholdMember)
admin.site.register(Category)
admin.site.register(Item)