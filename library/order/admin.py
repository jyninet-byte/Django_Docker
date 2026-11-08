from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from book.models import Book

from .models import Order


class StatusFilter(admin.SimpleListFilter):
    title = 'status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (('open', 'On hand'), ('overdue', 'Overdue'), ('closed', 'Returned'))

    def queryset(self, request, queryset):
        if self.value() == 'open':
            return queryset.filter(end_at__isnull=True)
        if self.value() == 'overdue':
            return queryset.filter(end_at__isnull=True, plated_end_at__lt=timezone.now())
        if self.value() == 'closed':
            return queryset.filter(end_at__isnull=False)
        return queryset


class BookIdFilter(admin.SimpleListFilter):
    title = 'book id'
    parameter_name = 'book_id'

    def lookups(self, request, model_admin):
        return [(book_id, f'#{book_id}') for book_id in Book.objects.order_by('id').values_list('id', flat=True)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(book_id=self.value())
        return queryset


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'book_id_col', 'book_title', 'book_authors', 'user', 'created_at',
                    'plated_end_at', 'end_at', 'status')
    list_display_links = ('id', 'book_title')
    list_filter = (StatusFilter, BookIdFilter,
                   ('book', admin.RelatedOnlyFieldListFilter),
                   ('book__authors', admin.RelatedFieldListFilter),
                   'created_at')
    search_fields = ('=id', '=book__id', 'book__name', 'book__authors__surname', 'user__email', 'user__last_name')
    search_help_text = 'Search by order ID, book ID, book title, author or reader'
    date_hierarchy = 'created_at'
    list_select_related = ('book', 'user')
    list_per_page = 25
    readonly_fields = ('id', 'created_at')
    actions = ('close_orders',)

    fieldsets = (
        ('Order', {'fields': ('id', 'book', 'user')}),
        ('Dates', {'fields': ('created_at', 'plated_end_at', 'end_at')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('book__authors')

    @admin.display(description='book id', ordering='book__id')
    def book_id_col(self, obj):
        return obj.book_id

    @admin.display(description='book title', ordering='book__name')
    def book_title(self, obj):
        return obj.book.name

    @admin.display(description='author')
    def book_authors(self, obj):
        return ', '.join(author.full_name for author in obj.book.authors.all()) or '—'

    @admin.display(description='status')
    def status(self, obj):
        if obj.end_at:
            return format_html('<span style="color:#666">returned</span>')
        if obj.is_overdue:
            return format_html('<b style="color:#ba2121">overdue</b>')
        return format_html('<b style="color:#1f7a4d">on hand</b>')

    @admin.action(description='Close selected orders (book returned)')
    def close_orders(self, request, queryset):
        updated = queryset.filter(end_at__isnull=True).update(end_at=timezone.now())
        self.message_user(request, f'{updated} order(s) closed.')
