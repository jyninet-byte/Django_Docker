from django.db import models, DataError

from authentication.models import CustomUser
from book.models import Book


class Order(models.Model):
    """
           This class represents an Order. \n
           Attributes:
           -----------
           param book: foreign key Book
           type book: ForeignKey
           param user: foreign key CustomUser
           type user: ForeignKey
           param created_at: Describes the date when the order was created. Can't be changed.
           type created_at: int (timestamp)
           param end_at: Describes the actual return date of the book. (`None` if not returned)
           type end_at: int (timestamp)
           param plated_end_at: Describes the planned return period of the book (2 weeks from the moment of creation).
           type plated_end_at: int (timestamp)
       """
    book = models.ForeignKey(Book, on_delete=models.CASCADE, default=None)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, default=None)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='date of issue')
    end_at = models.DateTimeField(default=None, null=True, blank=True, verbose_name='returned at')
    plated_end_at = models.DateTimeField(default=None, verbose_name='planned return date')

    class Meta:
        ordering = ['-created_at', '-id']

    @property
    def is_open(self):
        """True while the book has not been returned."""
        return self.end_at is None

    @property
    def is_overdue(self):
        """True if the book is not returned and the planned return date has passed."""
        from django.utils import timezone
        return self.end_at is None and self.plated_end_at < timezone.now()

    def __str__(self):
        """Human-readable name of the order (used in the admin panel)."""
        return f'Order #{self.pk}: {self.book.name} — {self.user.email}'

    def __repr__(self):
        """
        This magic method is redefined to show class and id of Book object.
        :return: class, id
        """
        return f'{self.__class__.__name__}(id={self.id})'

    def to_dict(self):
        """
                :return: order id, book id, user id, order created_at, order end_at, order plated_end_at
                :Example:
                | {
                |   'id': 8,
                |   'book': 8,
                |   'user': 8',
                |   'created_at': 1509393504,
                |   'end_at': 1509393504,
                |   'plated_end_at': 1509402866,
                | }
                """
        pass

    @staticmethod
    def create(user, book, plated_end_at):
        if user is None or user.pk is None or book is None or book.pk is None:
            return None
        active = Order.objects.filter(book=book, end_at__isnull=True).count()
        if active >= book.count:
            return None
        try:
            order = Order(user=user, book=book, plated_end_at=plated_end_at)
            order.save()
            return order
        except ValueError:
            return None
        except DataError:
            return None

    @staticmethod
    def get_by_id(order_id):
        try:
            return Order.objects.get(pk=order_id)
        except:
            return None

    def update(self, plated_end_at=None, end_at=None):
        if plated_end_at != None:
            self.plated_end_at = plated_end_at
        if end_at != None:
            self.end_at = end_at
        self.save()

    @staticmethod
    def get_all():
        return list(Order.objects.all())

    @staticmethod
    def get_not_returned_books():
        return Order.objects.filter(end_at=None).values()

    @staticmethod
    def delete_by_id(order_id):
        try:
            a = Order.objects.get(pk=order_id)
        except:
            return False
        else:
            a.delete()
            return True
