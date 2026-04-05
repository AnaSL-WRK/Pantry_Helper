from django.contrib import admin
from .models import Household, HouseholdMember, Category, Ingredient, Food, Recipe, RecipeIngredient, RecipeStep, WasteLog

# Register your models here.

admin.site.register(Household)
admin.site.register(HouseholdMember)
admin.site.register(Category)
admin.site.register(Ingredient)
admin.site.register(Food)
admin.site.register(Recipe)
admin.site.register(RecipeIngredient)
admin.site.register(RecipeStep)
admin.site.register(WasteLog)