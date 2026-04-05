#urls from app

from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('members/', views.household_members, name='household_members'),
    path('members/<int:member_id>/role/', views.household_member_change_role, name='household_member_change_role'),

    path('members/', views.household_members, name='household_members'),
    path('members/add/', views.household_member_add, name='household_member_add'),
    path('members/<int:member_id>/role/', views.household_member_change_role, name='household_member_change_role'),

    path('foods/', views.food_list, name='food_list'),
    path('foods/new/', views.food_new, name='food_new'),
    path('ingredients/new/', views.ingredient_new, name='ingredient_new'),
    
    path('recipes/', views.recipe_list, name='recipe_list'),
    path('recipes/<int:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('recipes/suggested/', views.suggested_recipes, name='suggested_recipes'),

    path('foods/<int:pk>/edit/', views.food_edit, name='food_edit'),
    path('foods/<int:pk>/delete/', views.food_delete, name='food_delete'),
    path('foods/<int:pk>/consume/', views.food_consume, name='food_consume'),
    path('foods/<int:pk>/waste/', views.food_waste, name='food_waste'),
]