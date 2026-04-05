from datetime import date, timedelta

from django.db import migrations
from django.contrib.auth.hashers import make_password


def load_demo_pantry_data(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Household = apps.get_model('app', 'Household')
    HouseholdMember = apps.get_model('app', 'HouseholdMember')
    Category = apps.get_model('app', 'Category')
    Ingredient = apps.get_model('app', 'Ingredient')
    Food = apps.get_model('app', 'Food')

    today = date.today()

    demo_user, _ = User.objects.get_or_create(
        username='demo_client',
        defaults={
            'email': 'demo_client@example.com',
            'password': make_password('demo1234'),
            'first_name': 'Demo',
            'last_name': 'Client',
            'is_staff': False,
            'is_superuser': False,
            'is_active': True,
        },
    )

    household, _ = Household.objects.get_or_create(
        name='Demo Household',
        defaults={
            'description': 'Sample household loaded for demo purposes.',
            'created_by': demo_user,
        },
    )

    HouseholdMember.objects.get_or_create(
        user=demo_user,
        defaults={'household': household},
    )

    sample_foods = [
        {'category': 'Dairy', 'ingredient': 'milk', 'quantity': 1, 'unit': 'l', 'location': 'FRIDGE', 'expiry_date': today - timedelta(days=2)},
        {'category': 'Dairy', 'ingredient': 'butter', 'quantity': 250, 'unit': 'g', 'location': 'FRIDGE', 'expiry_date': today + timedelta(days=365)},
        {'category': 'Meat', 'ingredient': 'streaky bacon', 'quantity': 200, 'unit': 'g', 'location': 'FRIDGE', 'expiry_date': today},
        {'category': 'Meat', 'ingredient': 'pork fillet', 'quantity': 400, 'unit': 'g', 'location': 'FRIDGE', 'expiry_date': today + timedelta(days=7)},
        {'category': 'Fish', 'ingredient': 'smoked salmon', 'quantity': 150, 'unit': 'g', 'location': 'FRIDGE', 'expiry_date': today - timedelta(days=1)},
        {'category': 'Fish', 'ingredient': 'salmon fillet', 'quantity': 300, 'unit': 'g', 'location': 'FRIDGE', 'expiry_date': today + timedelta(days=7)},
        {'category': 'Fruit', 'ingredient': 'apples', 'quantity': 6, 'unit': 'units', 'location': 'FRIDGE', 'expiry_date': today + timedelta(days=7)},
        {'category': 'Fruit', 'ingredient': 'orange', 'quantity': 4, 'unit': 'units', 'location': 'FRIDGE', 'expiry_date': today + timedelta(days=365)},
        {'category': 'Vegetables', 'ingredient': 'carrots', 'quantity': 1, 'unit': 'kg', 'location': 'FRIDGE', 'expiry_date': today},
        {'category': 'Vegetables', 'ingredient': 'red onion', 'quantity': 3, 'unit': 'units', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
        {'category': 'Bakery', 'ingredient': 'breadcrumbs', 'quantity': 250, 'unit': 'g', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
        {'category': 'Bakery', 'ingredient': 'puff pastry', 'quantity': 1, 'unit': 'pack', 'location': 'FRIDGE', 'expiry_date': today + timedelta(days=7)},
        {'category': 'Drinks', 'ingredient': 'apple juice', 'quantity': 1, 'unit': 'l', 'location': 'FRIDGE', 'expiry_date': today},
        {'category': 'Drinks', 'ingredient': 'white wine', 'quantity': 750, 'unit': 'ml', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
        {'category': 'Snacks', 'ingredient': 'flaked almonds', 'quantity': 150, 'unit': 'g', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
        {'category': 'Snacks', 'ingredient': 'walnuts', 'quantity': 200, 'unit': 'g', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
        {'category': 'Frozen', 'ingredient': 'frozen sweetcorn', 'quantity': 500, 'unit': 'g', 'location': 'FREEZER', 'expiry_date': today + timedelta(days=365)},
        {'category': 'Pantry', 'ingredient': 'plain flour', 'quantity': 1, 'unit': 'kg', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
        {'category': 'Pantry', 'ingredient': 'olive oil', 'quantity': 750, 'unit': 'ml', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
    ]

    for entry in sample_foods:
        category = Category.objects.get(name=entry['category'])

        ingredient, created = Ingredient.objects.get_or_create(
            name=entry['ingredient'],
            defaults={'category': category},
        )

        if not created and ingredient.category_id != category.id:
            ingredient.category = category
            ingredient.save(update_fields=['category'])

        Food.objects.update_or_create(
            household=household,
            ingredient=ingredient,
            defaults={
                'quantity': entry['quantity'],
                'unit': entry['unit'],
                'location': entry['location'],
                'expiry_date': entry['expiry_date'],
                'added_by': demo_user,
                'notes': 'Demo sample item',
            },
        )


def unload_demo_pantry_data(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Household = apps.get_model('app', 'Household')
    Food = apps.get_model('app', 'Food')
    HouseholdMember = apps.get_model('app', 'HouseholdMember')

    household = Household.objects.filter(name='Demo Household').first()
    if household is not None:
        Food.objects.filter(household=household).delete()
        HouseholdMember.objects.filter(household=household).delete()
        household.delete()

    User.objects.filter(username='demo_client').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_load_categories'),
    ]

    operations = [
        migrations.RunPython(load_demo_pantry_data, unload_demo_pantry_data),
    ]