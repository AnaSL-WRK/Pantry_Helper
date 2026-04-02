from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Food, Ingredient

#forms

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'category']

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()

        if not name:
            raise ValidationError('Ingredient name is required.')

        if Ingredient.objects.filter(name__iexact=name).exists():
            raise ValidationError('This ingredient already exists.')

        return name


class FoodForm(forms.ModelForm):
    class Meta:
        model = Food
        fields = ['ingredient', 'quantity', 'unit', 'location', 'expiry_date', 'notes']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ingredient'].queryset = Ingredient.objects.select_related('category').order_by('name')
        self.fields['ingredient'].empty_label = 'Select an ingredient'

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')

        if quantity is None or quantity <= 0:
            raise ValidationError('Quantity must be greater than 0.')

        return quantity

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')

        if expiry_date and expiry_date < timezone.localdate():
            raise ValidationError('Expiry date cannot be in the past.')

        return expiry_date