"""Django forms for creating and editing orders."""
import datetime

from django import forms
from django.utils import timezone

from .models import Order

MAX_ORDER_DAYS = 60
RETURN_HOUR = datetime.time(18, 0)
DATETIME_FORMAT = '%Y-%m-%dT%H:%M'


def to_return_datetime(date):
    """Planned return is stored as a datetime: the chosen day at 18:00 local time."""
    return timezone.make_aware(datetime.datetime.combine(date, RETURN_HOUR))


class DateInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, **kwargs):
        super().__init__(format='%Y-%m-%d', **kwargs)


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = 'datetime-local'

    def __init__(self, **kwargs):
        super().__init__(format=DATETIME_FORMAT, **kwargs)


class OrderCreateForm(forms.Form):
    """A reader orders a book and chooses the return date."""
    plated_end_at = forms.DateField(label='I will return it by', widget=DateInput(),
                                    help_text=f'Up to {MAX_ORDER_DAYS} days. Two weeks by default.')

    def __init__(self, *args, user=None, book=None, **kwargs):
        self.user, self.book = user, book
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        self.fields['plated_end_at'].initial = today + datetime.timedelta(days=14)
        self.fields['plated_end_at'].widget.attrs.update({
            'min': (today + datetime.timedelta(days=1)).isoformat(),
            'max': (today + datetime.timedelta(days=MAX_ORDER_DAYS)).isoformat(),
        })

    def clean_plated_end_at(self):
        date = self.cleaned_data['plated_end_at']
        today = timezone.localdate()
        if date <= today:
            raise forms.ValidationError('The return date must be in the future.')
        if date > today + datetime.timedelta(days=MAX_ORDER_DAYS):
            raise forms.ValidationError(f'You can take a book for {MAX_ORDER_DAYS} days at most.')
        return date

    def clean(self):
        cleaned = super().clean()
        if Order.objects.filter(user=self.user, book=self.book, end_at__isnull=True).exists():
            raise forms.ValidationError('You already have this book.')
        if self.book.available_count <= 0:
            raise forms.ValidationError('Sorry, there are no free copies of this book right now.')
        return cleaned

    def save(self):
        return Order.create(self.user, self.book, to_return_datetime(self.cleaned_data['plated_end_at']))


class OrderExtendForm(forms.ModelForm):
    """A reader changes the planned return date of his open order."""
    plated_end_at = forms.DateField(label='New return date', widget=DateInput())

    class Meta:
        model = Order
        fields = ('plated_end_at',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['plated_end_at'] = timezone.localtime(self.instance.plated_end_at).date()
        self.max_date = timezone.localtime(self.instance.created_at).date() + datetime.timedelta(days=MAX_ORDER_DAYS)
        self.fields['plated_end_at'].widget.attrs['max'] = self.max_date.isoformat()
        self.fields['plated_end_at'].help_text = f'Not later than {self.max_date:%d.%m.%Y} ({MAX_ORDER_DAYS} days from the date of issue).'

    def clean_plated_end_at(self):
        date = self.cleaned_data['plated_end_at']
        if date <= timezone.localdate():
            raise forms.ValidationError('The return date must be in the future.')
        if date > self.max_date:
            raise forms.ValidationError(f'The latest possible date is {self.max_date:%d.%m.%Y}.')
        return to_return_datetime(date)


class OrderEditForm(forms.ModelForm):
    """A librarian edits the dates of an order."""
    plated_end_at = forms.DateTimeField(label='Planned return date', widget=DateTimeLocalInput(),
                                        input_formats=[DATETIME_FORMAT])
    end_at = forms.DateTimeField(label='Returned at', widget=DateTimeLocalInput(), required=False,
                                 input_formats=[DATETIME_FORMAT],
                                 help_text='Leave empty while the book is not returned.')

    class Meta:
        model = Order
        fields = ('plated_end_at', 'end_at')

    def clean(self):
        cleaned = super().clean()
        # the form works with minutes, so compare with the date of issue without seconds
        created_at = self.instance.created_at.replace(second=0, microsecond=0)
        plated_end_at, end_at = cleaned.get('plated_end_at'), cleaned.get('end_at')
        if plated_end_at and plated_end_at <= created_at:
            self.add_error('plated_end_at', 'The planned return date must be after the date of issue.')
        if end_at and end_at < created_at:
            self.add_error('end_at', 'The book cannot be returned before it was issued.')
        if end_at and end_at > timezone.now():
            self.add_error('end_at', 'The return date cannot be in the future.')
        return cleaned
