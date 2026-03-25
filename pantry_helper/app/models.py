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
        related_name="created_households"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(User, related_name="households")   

    def __str__(self):
        return self.name
    
#each member(user) can only be in one household
#django.group going to give each role
#CRUD already created by default
class HouseholdMember(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="household_member"
    )

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="members"
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    #falta items e receitas
    class Meta:
        permissions = [
            ("manage_household_members", "Can manage household members"),
            ("change_member_role", "Can change household member role"),
        ]

    
    def __str__(self):
        return f"{self.user.username} -> {self.household.name}"