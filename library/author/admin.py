from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html, format_html_join

from .models import Author


class HasBooksFilter(admin.SimpleListFilter):
    title = 'books attached'
    parameter_name = 'has_books'

    def lookups(self, request, model_admin):
        return (('yes', 'Has books'), ('no', 'No books (can be removed)'))

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(books_total__gt=0)
        if self.value() == 'no':
            return queryset.filter(books_total=0)
        return queryset


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('id', 'surname', 'name', 'patronymic', 'books_count', 'book_titles')
    list_display_links = ('id', 'surname')
    list_filter = (HasBooksFilter, ('books', admin.RelatedFieldListFilter))
    search_fields = ('=id', 'surname', 'name', 'patronymic', 'books__name')
    search_help_text = 'Search by author ID, name or book title'
    ordering = ('surname', 'name')
    filter_horizontal = ('books',)
    readonly_fields = ('id', 'books_count', 'books_overview')

    fieldsets = (
        ('Personal information', {
            'fields': ('id', ('surname', 'name', 'patronymic')),
        }),
        ('Books', {
            'description': 'Choose the books written by this author.',
            'fields': ('books',),
        }),
        ('Overview', {
            'fields': ('books_count', 'books_overview'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(books_total=Count('books', distinct=True)) \
            .prefetch_related('books')

    @admin.display(description='books', ordering='books_total')
    def books_count(self, obj):
        return getattr(obj, 'books_total', None) or obj.books.count()

    @admin.display(description='titles')
    def book_titles(self, obj):
        return ', '.join(book.name for book in obj.books.all()) or '—'

    @admin.display(description='books in detail')
    def books_overview(self, obj):
        if not obj.pk or not obj.books.exists():
            return 'No books yet.'
        return format_html('<table><tr><th>ID</th><th>Title</th><th>Year</th><th>Copies</th></tr>{}</table>',
                           format_html_join('', '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>',
                                            ((b.id, b.name, b.year or '—', b.count) for b in obj.books.all())))
