"""Django form for adding and editing authors."""
from django import forms

from .models import Author


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ('surname', 'name', 'patronymic')
        labels = {'patronymic': 'Patronymic (optional)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['surname'].required = True
        self.fields['name'].required = True

    def clean(self):
        cleaned = super().clean()
        duplicates = Author.objects.filter(
            name__iexact=cleaned.get('name', ''), surname__iexact=cleaned.get('surname', ''),
            patronymic__iexact=cleaned.get('patronymic', ''))
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if cleaned.get('name') and cleaned.get('surname') and duplicates.exists():
            raise forms.ValidationError('This author already exists.')
        return cleaned
