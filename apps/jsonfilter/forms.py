from django import forms

class JSONInputForm(forms.Form):
    json_data = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Enter JSON data here'}),
        label='',
        required=True
    )
