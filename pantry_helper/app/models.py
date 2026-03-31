from django.db import models
from django.contrib.auth.models import User

# Create your models here.

#one household can have many members
class Household(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_households'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    
#each member(user) can only be in one household
#django.group going to give each role
#CRUD already created by default
class HouseholdMember(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='household_member'
    )
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='household_members'
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ('manage_household_members', 'Can manage household members'),
            ('change_member_role', 'Can change household member role'),
        ]

    def __str__(self):
        return f'{self.user.username} -> {self.household.name}'

#food category (food group) - dairy, meat, vegetables, etc
class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


#to use in recipes
class Ingredient(models.Model):
    name = models.CharField(max_length=120)

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingredients'
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


#food in pantry
class Food(models.Model):
    LOCATION_CHOICES = [
        ('FRIDGE', 'Fridge'),
        ('FREEZER', 'Freezer'),
        ('PANTRY', 'Pantry'),
    ]

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='foods'
    )

    #to link to recipes
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='foods'
    )

    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, default='units')
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, default='PANTRY')
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_foods'
    )

    class Meta:
        ordering = ['expiry_date', 'ingredient__name']
        permissions = [
            ('mark_food_consumed', 'Can mark a food item as consumed'),
            ('mark_food_wasted', 'Can mark a food item as wasted'),
        ]

    def __str__(self):
        return f'{self.ingredient.name} ({self.quantity} {self.unit})'



class Recipe(models.Model):
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name='recipes',
        null=True,
        blank=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_recipes'
    )

    name = models.CharField(max_length=200)
    author = models.CharField(max_length=120, blank=True)

    source_url = models.URLField(blank=True)
    source_site = models.CharField(max_length=100, blank=True)

    is_preloaded = models.BooleanField(default=False)

    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes'
    )

    class Meta:
        ordering = ['name']
        permissions = [
            ('view_suggested_recipes', 'Can view suggested recipes'),
        ]

    def __str__(self):
        return self.name



class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients'
    )

    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipe_links'
    )

    quantity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )

    unit = models.CharField(max_length=20, blank=True)

    line_text = models.TextField(blank=True)
    position = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['position']
        unique_together = ('recipe', 'position')

    def __str__(self):
        return f'{self.recipe.name} - {self.ingredient.name}'



class RecipeStep(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='steps'
    )
    step_text = models.TextField()
    position = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['position']
        unique_together = ('recipe', 'position')

    def __str__(self):
        return f'{self.recipe.name} - step {self.position}'