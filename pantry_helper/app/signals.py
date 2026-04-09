from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver

# after migrations 

ROLE_PERMISSIONS = {
    'Viewer': [
        'view_food',
        'view_ingredient',
        'view_recipe',
        'view_wastelog',
        'view_suggested_recipes',
    ],
    'Member': [
        'view_food',
        'view_ingredient',
        'view_recipe',
        'view_wastelog',
        'view_suggested_recipes',
        'mark_food_consumed',
        'mark_food_wasted',
    ],
    'InventoryManager': [
        'view_food',
        'view_ingredient',
        'view_recipe',
        'view_wastelog',
        'view_suggested_recipes',
        'mark_food_consumed',
        'mark_food_wasted',
        'add_food',
        'change_food',
        'delete_food',
        'add_ingredient',
    ],
    'HouseholdAdmin': [
        'view_food',
        'view_ingredient',
        'view_recipe',
        'view_wastelog',
        'view_suggested_recipes',
        'mark_food_consumed',
        'mark_food_wasted',
        'add_food',
        'change_food',
        'delete_food',
        'add_ingredient',
        'add_recipe',
        'change_recipe',
        'delete_recipe',
        'manage_household_members',
        'change_member_role',
        'add_household',
        'change_household',
    ],
}


@receiver(post_migrate, dispatch_uid='app.create_role_groups')
def create_role_groups(sender, app_config, **kwargs):
    if app_config.label != 'app':
        return

    for group_name, permission_codenames in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        permissions = Permission.objects.filter(
            content_type__app_label='app',
            codename__in=permission_codenames,
        )
        group.permissions.set(permissions)