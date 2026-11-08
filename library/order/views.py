from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from authentication.decorators import librarian_required, visitor_required
from book.models import Book
from book.views import book_detail_context

from .forms import OrderCreateForm, OrderEditForm, OrderExtendForm
from .models import Order

STATUSES = (
    ('', 'All'),
    ('open', 'Open'),
    ('overdue', 'Overdue'),
    ('closed', 'Closed'),
)


def _filter_by_status(orders, status):
    if status == 'open':
        return orders.filter(end_at__isnull=True)
    if status == 'overdue':
        return orders.filter(end_at__isnull=True, plated_end_at__lt=timezone.now())
    if status == 'closed':
        return orders.filter(end_at__isnull=False)
    return orders


@librarian_required
def order_list(request):
    """Show all orders (librarian only)."""
    status = request.GET.get('status', '')
    query = request.GET.get('q', '').strip()
    orders = Order.objects.select_related('book', 'user')
    orders = _filter_by_status(orders, status)
    if query:
        orders = orders.filter(Q(book__name__icontains=query) | Q(user__email__icontains=query)
                               | Q(user__last_name__icontains=query) | Q(user__first_name__icontains=query))
    return render(request, 'order/order_list.html',
                  {'orders': orders, 'status': status, 'statuses': STATUSES, 'query': query})


@login_required
def my_orders(request):
    """Show all orders of the current user."""
    status = request.GET.get('status', '')
    orders = _filter_by_status(Order.objects.filter(user=request.user).select_related('book'), status)
    return render(request, 'order/my_orders.html',
                  {'orders': orders, 'status': status, 'statuses': STATUSES})


@visitor_required
@require_POST
def order_create(request):
    """POST: validate OrderCreateForm and create an order (ordinary user only).

    If the form is invalid, the book page is shown again with the errors.
    """
    book = get_object_or_404(Book, pk=request.POST.get('book_id') or 0)
    form = OrderCreateForm(request.POST, user=request.user, book=book)
    if form.is_valid():
        order = form.save()
        if order is not None:
            messages.success(request, f'"{book.name}" is yours until '
                                      f'{timezone.localtime(order.plated_end_at):%d.%m.%Y}. Enjoy reading!')
            return redirect('my_orders')
        form.add_error(None, 'Sorry, there are no free copies of this book right now.')
    return render(request, 'book/book_detail.html', book_detail_context(request, book, order_form=form), status=400)


@visitor_required
def order_extend(request, order_id):
    """GET: form with the return date of my open order. POST: change the date (ordinary user only)."""
    order = get_object_or_404(Order.objects.select_related('book'), pk=order_id, user=request.user)
    if order.end_at is not None:
        messages.info(request, 'This order is already closed.')
        return redirect('my_orders')
    if request.method == 'POST':
        form = OrderExtendForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'New return date for "{order.book.name}": '
                                      f'{timezone.localtime(order.plated_end_at):%d.%m.%Y}.')
            return redirect('my_orders')
    else:
        form = OrderExtendForm(instance=order)
    return render(request, 'order/order_form.html', {'form': form, 'order': order, 'title': 'Change return date'})


@librarian_required
def order_edit(request, order_id):
    """GET: form with the dates of an order. POST: save the changes (librarian only)."""
    order = get_object_or_404(Order.objects.select_related('book', 'user'), pk=order_id)
    if request.method == 'POST':
        form = OrderEditForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'Order #{order.id} has been updated.')
            return redirect('order_list')
    else:
        form = OrderEditForm(instance=order)
    return render(request, 'order/order_form.html', {'form': form, 'order': order, 'title': f'Edit order #{order.id}'})


@librarian_required
@require_POST
def order_close(request, order_id):
    """Close an order - the book has been returned (librarian only)."""
    order = get_object_or_404(Order.objects.select_related('book'), pk=order_id)
    if order.end_at is not None:
        messages.info(request, f'Order #{order.id} is already closed.')
    else:
        order.update(end_at=timezone.now())
        messages.success(request, f'Order #{order.id} is closed. "{order.book.name}" is back in the library.')

    next_url = request.POST.get('next', '')
    if next_url.startswith('/') and not next_url.startswith('//'):
        return redirect(next_url)
    return redirect('order_list')
