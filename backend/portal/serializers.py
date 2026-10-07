from datetime import timedelta
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib.auth.password_validation import validate_password
import re
from rest_framework import serializers
from .models import Profile, Address, Service, ServiceArea, AvailabilitySlot, Offer, Product, Booking, Estimate, EstimateLine, StockMovement, Activity, JobPhoto, Invoice, Feedback

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    email = serializers.EmailField(required=True, allow_blank=False)
    phone = serializers.CharField(write_only=True, required=True, allow_blank=False)
    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value
    def validate_phone(self, value):
        digits = re.sub(r'\D', '', value)
        if len(digits) < 10 or len(digits) > 15:
            raise serializers.ValidationError('Enter a valid phone number with 10 to 15 digits.')
        return ('+' if value.strip().startswith('+') else '') + digits
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'password', 'phone']
    def create(self, data):
        phone = data.pop('phone')
        data['email'] = data['email'].strip().lower()
        user = User.objects.create_user(**data)
        Profile.objects.create(user=user, phone=phone)
        return user

class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role', 'phone']
        read_only_fields = ['username', 'role', 'phone']
    def get_role(self, user) -> str:
        return 'staff' if user.is_staff else getattr(getattr(user, 'profile', None), 'role', 'customer')
    def get_phone(self, user) -> str:
        return getattr(getattr(user, 'profile', None), 'phone', '')

class AddressSerializer(serializers.ModelSerializer):
    def validate_postal_code(self, value):
        value = value.strip()
        if not re.fullmatch(r'\d{6}', value):
            raise serializers.ValidationError('Enter a valid 6-digit PIN code.')
        return value
    class Meta:
        model = Address
        fields = ['id', 'label', 'line', 'city', 'postal_code']

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'

class ServiceAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceArea
        fields = ['id', 'name', 'city', 'postal_code', 'services', 'active']

class AvailabilitySlotSerializer(serializers.ModelSerializer):
    remaining = serializers.SerializerMethodField()
    class Meta:
        model = AvailabilitySlot
        fields = ['id', 'service', 'starts_at', 'ends_at', 'capacity', 'remaining', 'active']
    def get_remaining(self, slot) -> int:
        count = Booking.objects.filter(service=slot.service, preferred_at__gte=slot.starts_at, preferred_at__lt=slot.ends_at).exclude(status='Cancelled').count()
        return max(0, slot.capacity - count)

class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = ['id', 'code', 'title', 'description', 'service', 'discount_type', 'value', 'starts_at', 'ends_at', 'active']

class ProductSerializer(serializers.ModelSerializer):
    available = serializers.IntegerField(read_only=True)
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['stock', 'reserved']

class EstimateLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    class Meta:
        model = EstimateLine
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price', 'tax_rate', 'reserved', 'issued']
        read_only_fields = ['unit_price', 'tax_rate', 'reserved', 'issued']

class EstimateSerializer(serializers.ModelSerializer):
    lines = EstimateLineSerializer(many=True, read_only=True)
    class Meta:
        model = Estimate
        fields = ['id', 'booking', 'status', 'note', 'created_at', 'lines']

class ActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.username', read_only=True)
    class Meta:
        model = Activity
        fields = ['id', 'actor_name', 'message', 'created_at']

class JobPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPhoto
        fields = ['id', 'booking', 'image', 'caption', 'uploaded_by', 'created_at']
        read_only_fields = ['uploaded_by', 'created_at']
    def validate_image(self, value):
        if value.size > 5 * 1024 * 1024 or value.content_type not in ['image/jpeg', 'image/png', 'image/webp']:
            raise serializers.ValidationError('Upload a JPEG, PNG or WebP image under 5 MB.')
        return value

class BookingSerializer(serializers.ModelSerializer):
    issue = serializers.CharField(min_length=10, max_length=2000)
    activity = ActivitySerializer(many=True, read_only=True)
    job_photos = JobPhotoSerializer(many=True, read_only=True)
    estimates = EstimateSerializer(many=True, read_only=True)
    invoice = serializers.SerializerMethodField()
    service_name = serializers.CharField(source='service.name', read_only=True)
    address_text = serializers.CharField(source='address.line', read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['customer', 'technician', 'status', 'diagnosis', 'job_notes', 'labour_charge', 'labour_quoted', 'visit_quoted', 'tax_rate_quoted', 'offer_code_quoted', 'offer_discount_quoted', 'cancellation_request', 'reschedule_request', 'completed_at']
    def validate_address(self, value):
        request = self.context['request']
        if not request.user.is_staff and value.user_id != request.user.id:
            raise serializers.ValidationError('Choose your own saved address.')
        return value
    def validate_photo(self, value):
        if value and (value.size > 5 * 1024 * 1024 or value.content_type not in ['image/jpeg', 'image/png', 'image/webp']):
            raise serializers.ValidationError('Upload a JPEG, PNG or WebP image under 5 MB.')
        return value
    def validate_service(self, value):
        if not value.active:
            raise serializers.ValidationError('This service is unavailable.')
        return value
    def validate_preferred_at(self, value):
        from django.utils import timezone
        now = timezone.now()
        if value <= now:
            raise serializers.ValidationError('Choose a future date and time.')
        if value > now + timedelta(days=90):
            raise serializers.ValidationError('Bookings can be requested up to 90 days ahead.')
        return value
    def validate(self, attrs):
        from django.utils import timezone
        offer = attrs.get('offer')
        service = attrs.get('service')
        if offer and not offer.valid_for(service, timezone.now()):
            raise serializers.ValidationError({'offer': 'Offer is unavailable for this service or date.'})
        address = attrs.get('address')
        if ServiceArea.objects.filter(active=True).exists() and address and service:
            supported = ServiceArea.objects.filter(active=True, city__iexact=address.city, services=service).filter(Q(postal_code='') | Q(postal_code=address.postal_code)).exists()
            if not supported:
                raise serializers.ValidationError({'address': 'This service is not available at the selected address.'})
        return attrs
    def get_invoice(self, booking) -> dict | None:
        try:
            return InvoiceSerializer(booking.invoice).data
        except Invoice.DoesNotExist:
            return None
    def get_customer_name(self, booking) -> str:
        return booking.customer.get_full_name() or booking.customer.username
    def get_customer_phone(self, booking) -> str:
        return getattr(getattr(booking.customer, 'profile', None), 'phone', '')

class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ['id', 'product', 'booking', 'kind', 'quantity', 'note', 'actor', 'created_at']
        read_only_fields = ['actor', 'created_at']

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'booking', 'rating', 'comment', 'created_at']
        read_only_fields = ['created_at']
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating must be from 1 to 5.')
        return value

class InvoiceSerializer(serializers.ModelSerializer):
    charges = serializers.SerializerMethodField()
    class Meta:
        model = Invoice
        fields = ['id', 'booking', 'issued_at', 'payment_method', 'paid_at', 'charges']
        read_only_fields = ['issued_at', 'paid_at']
    def get_charges(self, invoice) -> dict:
        from decimal import Decimal
        booking = invoice.booking
        labour = booking.labour_charge if booking.labour_charge is not None else booking.labour_quoted
        visit = booking.visit_quoted
        discount = min(labour, booking.offer_discount_quoted)
        service_tax = (labour - discount + visit) * booking.tax_rate_quoted / Decimal('100')
        lines = []
        for line in EstimateLine.objects.select_related('product').filter(estimate__booking=booking, issued=True):
            base = line.unit_price * line.quantity
            tax = base * line.tax_rate / Decimal('100')
            lines.append({'product': line.product.name, 'sku': line.product.sku, 'quantity': line.quantity, 'unit_price': line.unit_price, 'base': base, 'tax': tax})
        total = labour - discount + visit + service_tax + sum((line['base'] + line['tax'] for line in lines), Decimal('0'))
        return {'labour': labour, 'visit': visit, 'discount': discount, 'offer_code': booking.offer_code_quoted, 'service_tax': service_tax, 'materials': lines, 'total': total}
