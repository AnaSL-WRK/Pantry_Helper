from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from app.models import Category, Food, Household, HouseholdMember, Ingredient


ROLE_GROUP_NAMES = ['Viewer', 'Member', 'InventoryManager', 'HouseholdAdmin']

DEMO_USERS = [
    {
        'username': 'demo_client',
        'email': 'demo_client@example.com',
        'first_name': 'Demo',
        'last_name': 'Client',
        'role': 'HouseholdAdmin',
    },
    {
        'username': 'demo_viewer',
        'email': 'demo_viewer@example.com',
        'first_name': 'Demo',
        'last_name': 'Viewer',
        'role': 'Viewer',
    },
    {
        'username': 'demo_member',
        'email': 'demo_member@example.com',
        'first_name': 'Demo',
        'last_name': 'Member',
        'role': 'Member',
    },
    {
        'username': 'demo_inventory',
        'email': 'demo_inventory@example.com',
        'first_name': 'Demo',
        'last_name': 'Inventory',
        'role': 'InventoryManager',
    },
]

DEMO_PASSWORD = 'demo1234'


class Command(BaseCommand):
    help = "Create or refresh demo users, household, and pantry sample data."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete the current demo user/household data before recreating it.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        if options['reset']:
            self._reset_demo_data(User)

        today = date.today()

        admin_config = next(user for user in DEMO_USERS if user['role'] == 'HouseholdAdmin')
        demo_user, created_user = self._upsert_demo_user(User, admin_config)

        household, created_household = Household.objects.get_or_create(
            name='Demo Household',
            defaults={
                'description': 'Sample household loaded for demo purposes.',
                'created_by': demo_user,
            },
        )

        if household.created_by_id is None:
            household.created_by = demo_user
            household.save(update_fields=['created_by'])

        HouseholdMember.objects.update_or_create(
            user=demo_user,
            defaults={'household': household},
        )

        self._assign_role(demo_user, 'HouseholdAdmin')

        created_extra_users = 0
        updated_extra_users = 0

        for user_config in DEMO_USERS:
            if user_config['role'] == 'HouseholdAdmin':
                continue

            role_user, role_user_created = self._upsert_demo_user(User, user_config)

            HouseholdMember.objects.update_or_create(
                user=role_user,
                defaults={'household': household},
            )

            self._assign_role(role_user, user_config['role'])

            if role_user_created:
                created_extra_users += 1
            else:
                updated_extra_users += 1

        sample_foods = [
            {'category': 'Dairy', 'ingredient': 'milk', 'quantity': 1, 'unit': 'liters', 'location': 'FRIDGE', 'expiry_date': today - timedelta(days=2)},
            {'category': 'Dairy', 'ingredient': 'butter', 'quantity': 250, 'unit': 'grams', 'location': 'FRIDGE', 'expiry_date': today + timedelta(days=365)},
            {'category': 'Meat', 'ingredient': 'streaky bacon', 'quantity': 200, 'unit': 'grams', 'location': 'FRIDGE', 'expiry_date': today},
            {'category': 'Meat', 'ingredient': 'pork fillet', 'quantity': 400, 'unit': 'grams', 'location': 'FRIDGE', 'expiry_date': today + timedelta(days=7)},
            {'category': 'Fish', 'ingredient': 'smoked salmon', 'quantity': 150, 'unit': 'grams', 'location': 'FRIDGE', 'expiry_date': today - timedelta(days=1)},
            {'category': 'Fish', 'ingredient': 'salmon fillet', 'quantity': 300, 'unit': 'grams', 'location': 'FRIDGE', 'expiry_date': today + timedelta(days=7)},
            {'category': 'Fruit', 'ingredient': 'apples', 'quantity': 6, 'unit': 'units', 'location': 'FRIDGE', 'expiry_date': today + timedelta(days=7)},
            {'category': 'Fruit', 'ingredient': 'oranges', 'quantity': 4, 'unit': 'units', 'location': 'FRIDGE', 'expiry_date': today + timedelta(days=365)},
            {'category': 'Vegetables', 'ingredient': 'carrots', 'quantity': 1, 'unit': 'kilograms', 'location': 'FRIDGE', 'expiry_date': today},
            {'category': 'Vegetables', 'ingredient': 'red onions', 'quantity': 3, 'unit': 'units', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
            {'category': 'Bakery', 'ingredient': 'breadcrumbs', 'quantity': 250, 'unit': 'grams', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
            {'category': 'Bakery', 'ingredient': 'puff pastry', 'quantity': 1, 'unit': 'packs', 'location': 'FRIDGE', 'expiry_date': today + timedelta(days=7)},
            {'category': 'Drinks', 'ingredient': 'apple juice', 'quantity': 1, 'unit': 'liters', 'location': 'FRIDGE', 'expiry_date': today},
            {'category': 'Drinks', 'ingredient': 'white wine', 'quantity': 750, 'unit': 'milliliters', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
            {'category': 'Snacks', 'ingredient': 'flaked almonds', 'quantity': 150, 'unit': 'grams', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
            {'category': 'Snacks', 'ingredient': 'walnuts', 'quantity': 200, 'unit': 'grams', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
            {'category': 'Frozen', 'ingredient': 'frozen sweetcorn', 'quantity': 500, 'unit': 'grams', 'location': 'FREEZER', 'expiry_date': today + timedelta(days=365)},
            {'category': 'Pantry', 'ingredient': 'plain flour', 'quantity': 1, 'unit': 'kilograms', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
            {'category': 'Pantry', 'ingredient': 'olive oil', 'quantity': 750, 'unit': 'milliliters', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
            {'category': 'Fruit', 'ingredient': 'clementines', 'quantity': 5, 'unit': 'units', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=2)},
            {'category': 'Fruit', 'ingredient': 'pomegranate seeds', 'quantity': 500, 'unit': 'grams', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=8)},
            {'category': 'Pantry', 'ingredient': 'ground cinnamon', 'quantity': 500, 'unit': 'grams', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
            {'category': 'Pantry', 'ingredient': 'porridge oats', 'quantity': 500, 'unit': 'grams', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=8)},
            {'category': 'Pantry', 'ingredient': 'sausages', 'quantity': 20, 'unit': 'units', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=8)},
            {'category': 'Pantry', 'ingredient': 'honey', 'quantity': 750, 'unit': 'milliliters', 'location': 'PANTRY', 'expiry_date': today + timedelta(days=365)},
        ]

        created_foods = 0
        updated_foods = 0

        for entry in sample_foods:
            category, _ = Category.objects.get_or_create(name=entry['category'])

            ingredient, ingredient_created = Ingredient.objects.get_or_create(
                name=entry['ingredient'],
                defaults={'category': category},
            )

            if not ingredient_created and ingredient.category_id is None:
                ingredient.category = category
                ingredient.save(update_fields=['category'])

            existing_food = (
                Food.objects
                .filter(household=household, ingredient=ingredient)
                .order_by('id')
                .first()
            )

            if existing_food:
                existing_food.quantity = entry['quantity']
                existing_food.unit = entry['unit']
                existing_food.location = entry['location']
                existing_food.expiry_date = entry['expiry_date']
                existing_food.added_by = demo_user
                existing_food.notes = 'Demo sample item'
                existing_food.save()

                Food.objects.filter(
                    household=household,
                    ingredient=ingredient
                ).exclude(pk=existing_food.pk).delete()

                updated_foods += 1
            else:
                Food.objects.create(
                    household=household,
                    ingredient=ingredient,
                    quantity=entry['quantity'],
                    unit=entry['unit'],
                    location=entry['location'],
                    expiry_date=entry['expiry_date'],
                    added_by=demo_user,
                    notes='Demo sample item',
                )
                created_foods += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready. "
                f"admin_created={created_user}, "
                f"extra_users_created={created_extra_users}, "
                f"extra_users_updated={updated_extra_users}, "
                f"household_created={created_household}, "
                f"foods_created={created_foods}, "
                f"foods_updated={updated_foods}"
            )
        )

        self.stdout.write("Demo credentials:")
        for user_config in DEMO_USERS:
            self.stdout.write(
                f"  - {user_config['username']} / {DEMO_PASSWORD} ({user_config['role']})"
            )

    def _assign_role(self, user, role_name):
        user.groups.remove(*Group.objects.filter(name__in=ROLE_GROUP_NAMES))
        role_group = Group.objects.filter(name=role_name).first()

        if role_group is None:
            self.stdout.write(
                self.style.WARNING(
                    f"{role_name} group was not found. "
                    "Run 'python manage.py migrate' first so role groups are created."
                )
            )
            return

        user.groups.add(role_group)

    def _upsert_demo_user(self, User, user_config):
        user, created = User.objects.get_or_create(
            username=user_config['username'],
            defaults={
                'email': user_config['email'],
                'first_name': user_config['first_name'],
                'last_name': user_config['last_name'],
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
            },
        )

        user.email = user_config['email']
        user.first_name = user_config['first_name']
        user.last_name = user_config['last_name']
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.set_password(DEMO_PASSWORD)
        user.save()

        return user, created

    def _reset_demo_data(self, User):
        demo_household = Household.objects.filter(name='Demo Household').first()
        demo_usernames = [user['username'] for user in DEMO_USERS]

        if demo_household:
            Food.objects.filter(household=demo_household).delete()
            HouseholdMember.objects.filter(household=demo_household).delete()
            demo_household.delete()

        User.objects.filter(username__in=demo_usernames).delete()

        self.stdout.write(self.style.WARNING("Previous demo data removed."))