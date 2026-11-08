from django.utils import timezone
from rest_framework import serializers

from authentication.models import ROLE_CHOICES, CustomUser
from author.models import Author
from book.models import Book
from order.models import Order


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=6,
                                     style={'input_type': 'password'})
    email = serializers.EmailField(max_length=100)
    role = serializers.ChoiceField(choices=ROLE_CHOICES, default=0)
    role_name = serializers.CharField(source='get_role_display', read_only=True)
    orders = serializers.PrimaryKeyRelatedField(source='order_set', many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'password', 'first_name', 'middle_name', 'last_name',
                  'role', 'role_name', 'is_active', 'created_at', 'updated_at', 'orders')
        read_only_fields = ('created_at', 'updated_at')
        extra_kwargs = {'is_active': {'default': True}}

    def validate_email(self, value):
        value = value.lower()
        users = CustomUser.objects.filter(email__iexact=value)
        if self.instance:
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'This field is required.'})
        request = self.context.get('request')
        if request and not (request.user.role == 1 or request.user.is_staff):
            # a reader cannot give himself the librarian role or (de)activate himself
            for field in ('role', 'is_active'):
                if field in attrs and getattr(self.instance, field, None) != attrs[field]:
                    raise serializers.ValidationError({field: 'Only a librarian can change this field.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        return CustomUser.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save()
        return instance


class AuthorSerializer(serializers.ModelSerializer):
    books = serializers.PrimaryKeyRelatedField(many=True, queryset=Book.objects.all(), required=False)

    class Meta:
        model = Author
        fields = ('id', 'name', 'surname', 'patronymic', 'books')
        extra_kwargs = {'name': {'required': True, 'allow_blank': False},
                        'surname': {'required': True, 'allow_blank': False}}


class BookSerializer(serializers.ModelSerializer):
    # the relation is stored in Author.books, so it is saved manually
    authors = serializers.PrimaryKeyRelatedField(many=True, queryset=Author.objects.all(), required=False)
    available = serializers.IntegerField(source='available_count', read_only=True)

    class Meta:
        model = Book
        fields = ('id', 'name', 'description', 'year', 'count', 'available', 'authors')
        extra_kwargs = {'name': {'required': True, 'allow_blank': False}}

    def validate_year(self, value):
        if value and value > timezone.localdate().year:
            raise serializers.ValidationError('The year cannot be in the future.')
        return value

    def validate_count(self, value):
        if value < 1:
            raise serializers.ValidationError('There must be at least one copy.')
        if self.instance and value < self.instance.active_orders_count:
            raise serializers.ValidationError(
                f'{self.instance.active_orders_count} copies are issued right now.')
        return value

    def create(self, validated_data):
        authors = validated_data.pop('authors', [])
        book = Book.objects.create(**validated_data)
        book.authors.set(authors)
        return book

    def update(self, instance, validated_data):
        authors = validated_data.pop('authors', None)
        instance = super().update(instance, validated_data)
        if authors is not None:
            instance.authors.set(authors)
        return instance


class OrderSerializer(serializers.ModelSerializer):
    """Order. `user` is optional for a reader (his own id is used)."""
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)

    class Meta:
        model = Order
        fields = ('id', 'user', 'book', 'created_at', 'plated_end_at', 'end_at')
        read_only_fields = ('created_at',)

    def validate(self, attrs):
        instance = self.instance
        book = attrs.get('book', getattr(instance, 'book', None))
        plated_end_at = attrs.get('plated_end_at', getattr(instance, 'plated_end_at', None))
        end_at = attrs.get('end_at', getattr(instance, 'end_at', None))
        created_at = instance.created_at if instance else timezone.now()

        if plated_end_at and plated_end_at <= created_at:
            raise serializers.ValidationError({'plated_end_at': 'Must be later than the date of issue.'})
        if end_at and end_at < created_at:
            raise serializers.ValidationError({'end_at': 'The book cannot be returned before it was issued.'})

        if instance is None or (book and book != instance.book):
            if book.available_count <= 0:
                raise serializers.ValidationError({'book': 'There are no free copies of this book.'})
        return attrs


class UserOrderSerializer(OrderSerializer):
    """Order inside /user/{id}/order/: the user comes from the URL."""
    user = serializers.PrimaryKeyRelatedField(read_only=True)
