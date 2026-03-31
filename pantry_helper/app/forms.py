from django import forms
from .models import Food

#forms

class FoodForm(forms.ModelForm):
    class Meta:
        model = Food
        fields = ['ingredient', 'quantity', 'unit', 'location', 'expiry_date', 'notes']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }