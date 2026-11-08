from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import Count, F, Max, Q
from django.utils.html import format_html, format_html_join

from author.models import Author
from order.models import Order

from .models import Book


class TitleLetterFilter(admin.SimpleListFilter):
    """Filter books by the first letter of the title."""
    title = 'book title (first letter)'
    parameter_name = 'letter'

    def lookups(self, request, model_admin):
        letters = sorted({name[:1].upper() for name in Book.objects.values_list('name', flat=True) if name})
        return [(letter, letter) for letter in letters]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(name__istartswith=self.value())
        return queryset


class AvailabilityFilter(admin.SimpleListFilter):
    title = 'availability'
    parameter_name = 'availability'

    def lookups(self, request, model_admin):
        return (('available', 'Has free copies'), ('taken', 'All copies issued'))

    def queryset(self, request, queryset):
        if self.value() == 'available':
            return queryset.filter(free_copies__gt=0)
        if self.value() == 'taken':
            return queryset.filter(free_copies__lte=0)
        return queryset


class WrappedFilteredSelectMultiple(FilteredSelectMultiple):
    """FilteredSelectMultiple inside the same wrapper the admin uses for model M2M fields."""

    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        return format_html('<div class="related-widget-wrapper">{}</div>', html)


class BookAdminForm(forms.ModelForm):
    """Book form with an 'authors' field (the relation is stored in Author.books)."""
    authors = forms.ModelMultipleChoiceField(
        queryset=Author.objects.all(),
        required=False,
        widget=WrappedFilteredSelectMultiple('authors', is_stacked=False),
    )

    class Meta:
        model = Book
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['authors'].initial = self.instance.authors.all()


class BookIssueInline(admin.TabularInline):
    """Changing data: every issue of the book with its dates."""
    model = Order
    extra = 0
    fields = ('user', 'created_at', 'plated_end_at', 'end_at', 'status')
    readonly_fields = ('created_at', 'status')
    verbose_name = 'issue'
    verbose_name_plural = 'Issues of this book (date of issue and return)'
    show_change_link = True

    @admin.display(description='status')
    def status(self, obj):
        if not obj.pk:
            return '—'
        if obj.end_at:
            return 'returned'
        return 'overdue' if obj.is_overdue else 'on hand'


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    form = BookAdminForm
    inlines = (BookIssueInline,)

    list_display = ('id', 'name', 'authors_list', 'year', 'count', 'issued_now', 'free_now', 'last_issue')
    list_display_links = ('id', 'name')
    list_filter = (('authors', admin.RelatedFieldListFilter), TitleLetterFilter, AvailabilityFilter, 'year')
    search_fields = ('=id', 'name', 'authors__surname', 'authors__name')
    search_help_text = 'Search by book ID, title or author'
    ordering = ('id',)
    list_per_page = 25
    readonly_fields = ('id', 'issued_now', 'free_now', 'last_issue', 'issue_history')

    fieldsets = (
        ('Permanent information', {
            'description': 'Data that does not change: title, authors, year of publication.',
            'fields': ('id', 'name', 'authors', 'year', 'description'),
        }),
        ('Changing information', {
            'description': 'Data that changes when the book is issued or returned.',
            'fields': ('count', 'issued_now', 'free_now', 'last_issue', 'issue_history'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('authors').annotate(
            issued=Count('order', filter=Q(order__end_at__isnull=True), distinct=True),
            last_issue_at=Max('order__created_at'),
        ).annotate(free_copies=F('count') - F('issued'))

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.authors.set(form.cleaned_data['authors'])

    @admin.display(description='authors')
    def authors_list(self, obj):
        return ', '.join(author.full_name for author in obj.authors.all()) or '—'

    @admin.display(description='issued now', ordering='issued')
    def issued_now(self, obj):
        return getattr(obj, 'issued', obj.active_orders_count)

    @admin.display(description='free copies', ordering='free_copies')
    def free_now(self, obj):
        free = getattr(obj, 'free_copies', obj.available_count)
        colour = '#1f7a4d' if free > 0 else '#ba2121'
        return format_html('<b style="color:{}">{}</b>', colour, free)

    @admin.display(description='last date of issue', ordering='last_issue_at')
    def last_issue(self, obj):
        last = getattr(obj, 'last_issue_at', None)
        if last is None and obj.pk:
            last = obj.order_set.aggregate(last=Max('created_at'))['last']
        return last.strftime('%d.%m.%Y %H:%M') if last else '—'

    @admin.display(description='who has the book now')
    def issue_history(self, obj):
        if not obj.pk:
            return '—'
        orders = obj.order_set.filter(end_at__isnull=True).select_related('user')
        if not orders:
            return 'All copies are in the library.'
        return format_html('<ul style="margin:0;padding-left:18px">{}</ul>', format_html_join(
            '', '<li>{} — issued {}, return by {}</li>',
            ((o.user.email, o.created_at.strftime('%d.%m.%Y'), o.plated_end_at.strftime('%d.%m.%Y'))
             for o in orders)))
