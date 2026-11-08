from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render

from authentication.decorators import librarian_required
from authentication.models import CustomUser
from order.forms import OrderCreateForm
from order.models import Order

from .forms import BookFilterForm, BookForm
from .models import Book


@login_required
def book_list(request):
    """GET: list of books filtered with BookFilterForm (title, author, description, availability)."""
    form = BookFilterForm(request.GET or None)
    books = Book.objects.prefetch_related('authors').annotate(
        taken=Count('order', filter=Q(order__end_at__isnull=True), distinct=True),
    ).annotate(available=F('count') - F('taken'))

    sort = 'name'
    is_filtered = False
    if form.is_bound and form.is_valid():
        data = form.cleaned_data
        if data['q']:
            books = books.filter(name__icontains=data['q'])
        if data['author']:
            books = books.filter(authors=data['author'])
        if data['description']:
            books = books.filter(description__icontains=data['description'])
        if data['available']:
            books = books.filter(available__gt=0)
        sort = data['sort'] or 'name'
        is_filtered = any(data[key] for key in ('q', 'author', 'description', 'available'))

    order_by = [F('year').desc(nulls_last=True)] if sort == '-year' else [sort]
    books = books.order_by(*order_by, 'id').distinct()
    return render(request, 'book/book_list.html', {'books': books, 'form': form, 'is_filtered': is_filtered})


def book_detail_context(request, book, order_form=None):
    """Context for the book page (shared with order.views.order_create)."""
    context = {'book': book}
    if request.user.is_librarian:
        context['open_orders'] = book.order_set.filter(end_at__isnull=True).select_related('user')
    else:
        context['my_open_order'] = book.order_set.filter(user=request.user, end_at__isnull=True).first()
        context['order_form'] = order_form or OrderCreateForm(user=request.user, book=book)
    return context


@login_required
def book_detail(request, book_id):
    """Show a specific book."""
    book = get_object_or_404(Book.objects.prefetch_related('authors'), pk=book_id)
    return render(request, 'book/book_detail.html', book_detail_context(request, book))


@librarian_required
def book_create(request):
    """GET: empty book form. POST: validate it and add the book (librarian only)."""
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save()
            messages.success(request, f'Book "{book.name}" has been added.')
            return redirect('book_detail', book_id=book.id)
    else:
        form = BookForm()
    return render(request, 'book/book_form.html', {'form': form})


@librarian_required
def book_edit(request, book_id):
    """GET: form filled with the book data. POST: save the changes (librarian only)."""
    book = get_object_or_404(Book, pk=book_id)
    if request.method == 'POST':
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, f'Book "{book.name}" has been updated.')
            return redirect('book_detail', book_id=book.id)
    else:
        form = BookForm(instance=book)
    return render(request, 'book/book_form.html', {'form': form, 'book': book})


@librarian_required
def user_books(request, user_id):
    """Show all books provided to a specific user (librarian only)."""
    reader = get_object_or_404(CustomUser, pk=user_id)
    orders = Order.objects.filter(user=reader).select_related('book').prefetch_related('book__authors')
    context = {
        'reader': reader,
        'open_orders': orders.filter(end_at__isnull=True),
        'closed_orders': orders.filter(end_at__isnull=False),
    }
    return render(request, 'book/user_books.html', context)
