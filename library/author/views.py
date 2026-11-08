from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from authentication.decorators import librarian_required

from .forms import AuthorForm
from .models import Author


def _authors():
    return Author.objects.annotate(books_count=Count('books')).prefetch_related('books')


@librarian_required
def author_list(request):
    """GET: all authors and an empty form for a new one (librarian only)."""
    return render(request, 'author/author_list.html', {'authors': _authors(), 'form': AuthorForm()})


@librarian_required
@require_POST
def author_create(request):
    """POST: validate the form and create a new author (librarian only)."""
    form = AuthorForm(request.POST)
    if form.is_valid():
        author = form.save()
        messages.success(request, f'Author {author.full_name} has been added.')
        return redirect('author_list')
    messages.error(request, 'Please correct the errors in the form.')
    return render(request, 'author/author_list.html', {'authors': _authors(), 'form': form}, status=400)


@librarian_required
def author_edit(request, author_id):
    """GET: form filled with the author data. POST: save the changes (librarian only)."""
    author = get_object_or_404(Author, pk=author_id)
    if request.method == 'POST':
        form = AuthorForm(request.POST, instance=author)
        if form.is_valid():
            form.save()
            messages.success(request, f'Author {author.full_name} has been updated.')
            return redirect('author_list')
    else:
        form = AuthorForm(instance=author)
    return render(request, 'author/author_form.html', {'form': form, 'author': author})


@librarian_required
@require_POST
def author_delete(request, author_id):
    """Remove an author if he is not attached to any book (librarian only)."""
    author = get_object_or_404(Author, pk=author_id)
    books_count = author.books.count()
    if books_count:
        messages.error(request, f'{author.full_name} cannot be removed: '
                                f'the author is attached to {books_count} book(s).')
    else:
        name = author.full_name
        author.delete()
        messages.success(request, f'Author {name} has been removed.')
    return redirect('author_list')
