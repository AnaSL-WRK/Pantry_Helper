# Demo pantry data migration
from django.db import migrations
from django.contrib.auth.hashers import make_password


def load_demo_pantry_data(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Household = apps.get_model('app', 'Household')
    HouseholdMember = apps.get_model('app', 'HouseholdMember')
    Ingredient = apps.get_model('app', 'Ingredient')
    Food = apps.get_model('app', 'Food')

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
        {'category': 'Dairy', 'ingredient': 'milk', 'quantity': '1.00', 'unit': 'l', 'location': 'FRIDGE'},
        {'category': 'Dairy', 'ingredient': 'butter', 'quantity': '250.00', 'unit': 'g', 'location': 'FRIDGE'},
        {'category': 'Meat', 'ingredient': 'streaky bacon', 'quantity': '200.00', 'unit': 'g', 'location': 'FRIDGE'},
        {'category': 'Meat', 'ingredient': 'pork fillet', 'quantity': '400.00', 'unit': 'g', 'location': 'FRIDGE'},
        {'category': 'Fish', 'ingredient': 'smoked salmon', 'quantity': '150.00', 'unit': 'g', 'location': 'FRIDGE'},
        {'category': 'Fish', 'ingredient': 'salmon fillet', 'quantity': '300.00', 'unit': 'g', 'location': 'FRIDGE'},
        {'category': 'Fruit', 'ingredient': 'apples', 'quantity': '6.00', 'unit': 'units', 'location': 'FRIDGE'},
        {'category': 'Fruit', 'ingredient': 'orange', 'quantity': '4.00', 'unit': 'units', 'location': 'FRIDGE'},
        {'category': 'Vegetables', 'ingredient': 'carrots', 'quantity': '1.00', 'unit': 'kg', 'location': 'FRIDGE'},
        {'category': 'Vegetables', 'ingredient': 'red onion', 'quantity': '3.00', 'unit': 'units', 'location': 'PANTRY'},
        {'category': 'Bakery', 'ingredient': 'breadcrumbs', 'quantity': '250.00', 'unit': 'g', 'location': 'PANTRY'},
        {'category': 'Bakery', 'ingredient': 'pack puff pastry', 'quantity': '1.00', 'unit': 'pack', 'location': 'FRIDGE'},
        {'category': 'Drinks', 'ingredient': 'apple juice', 'quantity': '1.00', 'unit': 'l', 'location': 'FRIDGE'},
        {'category': 'Drinks', 'ingredient': 'white wine', 'quantity': '750.00', 'unit': 'ml', 'location': 'PANTRY'},
        {'category': 'Snacks', 'ingredient': 'flaked almonds', 'quantity': '150.00', 'unit': 'g', 'location': 'PANTRY'},
        {'category': 'Snacks', 'ingredient': 'walnuts', 'quantity': '200.00', 'unit': 'g', 'location': 'PANTRY'},
        {'category': 'Frozen', 'ingredient': 'frozen sweetcorn', 'quantity': '500.00', 'unit': 'g', 'location': 'FREEZER'},
        {'category': 'Pantry', 'ingredient': 'plain flour', 'quantity': '1.00', 'unit': 'kg', 'location': 'PANTRY'},
        {'category': 'Pantry', 'ingredient': 'olive oil', 'quantity': '750.00', 'unit': 'ml', 'location': 'PANTRY'},
    ]

    for entry in sample_foods:
        ingredient = Ingredient.objects.filter(name=entry['ingredient']).first()
        if ingredient is None:
            continue

        Food.objects.get_or_create(
            household=household,
            ingredient=ingredient,
            defaults={
                'quantity': entry['quantity'],
                'unit': entry['unit'],
                'location': entry['location'],
                'added_by': demo_user,
                'notes': f"Demo sample for {entry['category']}",
            },
        )


def unload_demo_pantry_data(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Household = apps.get_model('app', 'Household')
    Food = apps.get_model('app', 'Food')

    household = Household.objects.filter(name='Demo Household').first()
    if household is not None:
        Food.objects.filter(household=household).delete()
        household.delete()

    User.objects.filter(username='demo_client').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_load_recipe_ingredients'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(load_demo_pantry_data, unload_demo_pantry_data),
    ]
