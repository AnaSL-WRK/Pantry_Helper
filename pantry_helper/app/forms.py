from django import forms
from .models import Category, Item


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['category', 'name', 'quantity', 'unit', 'location', 'expiry_date', 'notes']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
