"""Django forms for adding, editing and filtering books."""
from django import forms
from django.utils import timezone

from author.models import Author

from .models import Book


class AuthorChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.full_name


class BookForm(forms.ModelForm):
    """Add or edit a book. Authors are stored in Author.books, so the field is handled manually."""
    authors = AuthorChoiceField(
        queryset=Author.objects.all(), required=False,
        widget=forms.CheckboxSelectMultiple, label='Authors')

    class Meta:
        model = Book
        fields = ('name', 'description', 'year', 'count')
        labels = {'name': 'Title', 'year': 'Year of publication (optional)', 'count': 'Number of copies'}
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}
        help_texts = {'description': 'Up to 256 characters.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['year'].widget.attrs.update({'min': 1, 'max': timezone.localdate().year})
        self.fields['count'].widget.attrs['min'] = 1
        if self.instance.pk:
            self.fields['authors'].initial = list(self.instance.authors.values_list('pk', flat=True))

    def clean_year(self):
        year = self.cleaned_data.get('year')
        if year and year > timezone.localdate().year:
            raise forms.ValidationError('The year cannot be in the future.')
        return year

    def clean_count(self):
        count = self.cleaned_data['count']
        if count < 1:
            raise forms.ValidationError('There must be at least one copy.')
        if self.instance.pk:
            issued = self.instance.active_orders_count
            if count < issued:
                raise forms.ValidationError(
                    f'{issued} copies are issued right now, so the number cannot be less than {issued}.')
        return count

    def save(self, commit=True):
        book = super().save(commit=commit)
        if commit:
            book.authors.set(self.cleaned_data['authors'])
        return book


class BookFilterForm(forms.Form):
    """GET form with filters for the list of books."""
    SORT_CHOICES = (
        ('name', 'Title A-Z'),
        ('-name', 'Title Z-A'),
        ('-year', 'Newest publication'),
        ('-count', 'Most copies'),
        ('-id', 'Recently added'),
    )

    q = forms.CharField(required=False, label='Title',
                        widget=forms.TextInput(attrs={'type': 'search', 'placeholder': 'e.g. Kobzar'}))
    author = forms.ModelChoiceField(queryset=Author.objects.all(), required=False,
                                    empty_label='Any author', label='Author')
    description = forms.CharField(required=False, label='Description contains',
                                  widget=forms.TextInput(attrs={'type': 'search', 'placeholder': 'e.g. poetry'}))
    available = forms.BooleanField(required=False, label='Only available now')
    sort = forms.ChoiceField(choices=SORT_CHOICES, required=False, label='Sort by')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['author'].label_from_instance = lambda author: author.full_name
