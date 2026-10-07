from decimal import Decimal
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import connection, transaction
from django.db.models import Count, F, Sum
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework import serializers as rf_serializers
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import Address, Service, ServiceArea, AvailabilitySlot, Offer, Product, Booking, Estimate, EstimateLine, StockMovement, Activity, JobPhoto, Invoice, Feedback
from .serializers import RegisterSerializer, UserSerializer, AddressSerializer, ServiceSerializer, ServiceAreaSerializer, AvailabilitySlotSerializer, OfferSerializer, ProductSerializer, BookingSerializer, EstimateSerializer, StockMovementSerializer, JobPhotoSerializer, FeedbackSerializer, InvoiceSerializer
from .throttles import BookingCreateThrottle, LoginThrottle, RegisterThrottle

def is_staff(user):
    return user.is_staff

def is_technician(user):
    return getattr(getattr(user, 'profile', None), 'role', '') == 'technician'

def can_work(user, booking):
    return is_staff(user) or (is_technician(user) and booking.technician_id == user.id)

def log(booking, actor, message):
    Activity.objects.create(booking=booking, actor=actor, message=message)

def release_reservations(booking, actor):
    for line in EstimateLine.objects.select_related('product').filter(estimate__booking=booking, reserved=True, issued=False):
        product = Product.objects.select_for_update().get(pk=line.product_id)
        product.reserved -= line.quantity
        product.save(update_fields=['reserved'])
        line.reserved = False
        line.save(update_fields=['reserved'])
        StockMovement.objects.create(product=product, booking=booking, kind='release', quantity=line.quantity, actor=actor)

AuthRequest = inline_serializer(name='AuthRequest', fields={'username': rf_serializers.CharField(), 'password': rf_serializers.CharField()})
AuthResponse = inline_serializer(name='AuthResponse', fields={'token': rf_serializers.CharField(), 'user': UserSerializer()})
ConfigResponse = inline_serializer(name='ConfigResponse', fields={'payment_mode': rf_serializers.CharField(), 'email': rf_serializers.CharField(), 'sms': rf_serializers.CharField(), 'whatsapp': rf_serializers.CharField()})

@extend_schema(responses=ConfigResponse)
@api_view(['GET'])
@permission_classes([AllowAny])
def public_config(request):
    return Response({'payment_mode': 'cash or pay after service only; online gateway integration pending', 'email': 'provider settings present; delivery integration pending' if settings.EMAIL_HOST else 'not configured', 'sms': 'provider settings present; delivery integration pending' if settings.SMS_PROVIDER else 'not configured', 'whatsapp': 'provider settings present; delivery integration pending' if settings.WHATSAPP_PROVIDER else 'not configured'})

@extend_schema(responses=inline_serializer(name='HealthResponse', fields={'status': rf_serializers.CharField()}))
@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        cursor.fetchone()
    return Response({'status': 'ok'})

@extend_schema(request=RegisterSerializer, responses=AuthResponse)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegisterThrottle])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response({'token': Token.objects.create(user=user).key, 'user': UserSerializer(user).data}, status=201)

@extend_schema(request=AuthRequest, responses=AuthResponse)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def login(request):
    user = authenticate(username=request.data.get('username'), password=request.data.get('password'))
    if not user or not user.is_active:
        raise ValidationError('Invalid username or password.')
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': UserSerializer(user).data})

@extend_schema(request=None, responses=inline_serializer(name='LogoutResponse', fields={'detail': rf_serializers.CharField()}))
@api_view(['POST'])
def logout(request):
    if request.auth:
        request.auth.delete()
    return Response({'detail': 'Signed out.'})

@extend_schema(request=UserSerializer, responses=UserSerializer)
@api_view(['GET', 'PATCH'])
def me(request):
    if request.method == 'PATCH':
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return Response(UserSerializer(request.user).data)

class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    queryset = Address.objects.all()
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceSerializer
    queryset = Service.objects.all()
    permission_classes = [AllowAny]
    def get_queryset(self):
        q = Service.objects.all() if self.request.user.is_staff else Service.objects.filter(active=True)
        if self.request.query_params.get('category'):
            q = q.filter(category=self.request.query_params['category'])
        if self.request.query_params.get('search'):
            q = q.filter(name__icontains=self.request.query_params['search'])
        if self.request.query_params.get('max_price'):
            q = q.filter(labour_price__lte=self.request.query_params['max_price'])
        if self.request.query_params.get('area'):
            q = q.filter(areas__id=self.request.query_params['area'], areas__active=True)
        return q.order_by('name')
    def perform_create(self, serializer):
        if not is_staff(self.request.user): raise PermissionDenied()
        serializer.save()
    def perform_update(self, serializer):
        if not is_staff(self.request.user): raise PermissionDenied()
        serializer.save()
    def perform_destroy(self, instance):
        if not is_staff(self.request.user): raise PermissionDenied()
        instance.active = False; instance.save(update_fields=['active'])

class ServiceAreaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServiceAreaSerializer
    queryset = ServiceArea.objects.all()
    permission_classes = [AllowAny]
    def get_queryset(self):
        return ServiceArea.objects.filter(active=True).prefetch_related('services').order_by('name')

class AvailabilityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AvailabilitySlotSerializer
    queryset = AvailabilitySlot.objects.all()
    permission_classes = [AllowAny]
    def get_queryset(self):
        q = AvailabilitySlot.objects.filter(active=True, ends_at__gt=timezone.now()).select_related('service').order_by('starts_at')
        if self.request.query_params.get('service'):
            q = q.filter(service_id=self.request.query_params['service'])
        if self.request.query_params.get('date'):
            q = q.filter(starts_at__date=self.request.query_params['date'])
        return q

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    permission_classes = [AllowAny]
    def get_queryset(self):
        q = Product.objects.all() if self.request.user.is_staff else Product.objects.filter(active=True)
        for field in ['category', 'brand']:
            if self.request.query_params.get(field): q = q.filter(**{field: self.request.query_params[field]})
        if self.request.query_params.get('search'): q = q.filter(name__icontains=self.request.query_params['search'])
        if self.request.query_params.get('max_price'): q = q.filter(price__lte=self.request.query_params['max_price'])
        return q.order_by('name')
    def perform_create(self, serializer):
        if not is_staff(self.request.user): raise PermissionDenied()
        serializer.save()
    def perform_update(self, serializer):
        if not is_staff(self.request.user): raise PermissionDenied()
        serializer.save()
    def perform_destroy(self, instance):
        if not is_staff(self.request.user): raise PermissionDenied()
        instance.active = False; instance.save(update_fields=['active'])

class OfferViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OfferSerializer
    queryset = Offer.objects.all()
    permission_classes = [AllowAny]
    def get_queryset(self):
        now = timezone.now()
        return Offer.objects.filter(active=True, starts_at__lte=now, ends_at__gte=now).order_by('ends_at')

class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    def get_throttles(self):
        if getattr(self, 'action', None) == 'create':
            return [BookingCreateThrottle()]
        return super().get_throttles()
    queryset = Booking.objects.all()
    http_method_names = ['get', 'post', 'head', 'options']
    def get_queryset(self):
        q = Booking.objects.select_related('service', 'address', 'customer', 'technician').prefetch_related('activity', 'estimates__lines')
        if is_staff(self.request.user): pass
        elif is_technician(self.request.user): q = q.filter(technician=self.request.user)
        else: q = q.filter(customer=self.request.user)
        if self.request.query_params.get('status'): q = q.filter(status=self.request.query_params['status'])
        return q.order_by('-created_at')
    def perform_create(self, serializer):
        service = serializer.validated_data['service']
        offer = serializer.validated_data.get('offer')
        discount = Decimal('0')
        if offer:
            discount = min(service.labour_price, service.labour_price * offer.value / Decimal('100')) if offer.discount_type == 'percent' else min(service.labour_price, offer.value)
        with transaction.atomic():
            Service.objects.select_for_update().get(pk=service.pk)
            requested = serializer.validated_data['preferred_at']
            slots = AvailabilitySlot.objects.filter(service=service, active=True, ends_at__gt=timezone.now())
            if slots.exists():
                slot = slots.filter(starts_at__lte=requested, ends_at__gt=requested).first()
                if not slot:
                    raise ValidationError('Choose a published available time slot.')
                count = Booking.objects.filter(service=service, preferred_at__gte=slot.starts_at, preferred_at__lt=slot.ends_at).exclude(status='Cancelled').count()
                if count >= slot.capacity:
                    raise ValidationError('This time slot is full. Please choose another.')
            booking = serializer.save(customer=self.request.user, labour_quoted=service.labour_price, visit_quoted=service.visit_price, tax_rate_quoted=service.tax_rate, offer_code_quoted=offer.code if offer else '', offer_discount_quoted=discount)
            log(booking, self.request.user, 'Booking requested')

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        if not is_staff(request.user): raise PermissionDenied()
        from django.contrib.auth.models import User
        booking = self.get_object()
        technician = User.objects.filter(pk=request.data.get('technician')).first()
        if not technician or not is_technician(technician): raise ValidationError('Choose a technician account.')
        booking.technician = technician; booking.status = 'Assigned'; booking.save(update_fields=['technician', 'status'])
        log(booking, request.user, f'Assigned to {technician.username}')
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=['post'])
    def transition(self, request, pk=None):
        booking = self.get_object()
        target = request.data.get('status')
        allowed = {'New': ['Confirmed', 'Cancelled'], 'Confirmed': ['Assigned', 'Cancelled'], 'Assigned': ['Accepted', 'Cancelled'], 'Accepted': ['In Progress', 'Cancelled'], 'In Progress': ['Inspection Required', 'Estimate Awaiting Approval', 'Material Pending', 'Completed'], 'Inspection Required': ['Estimate Awaiting Approval', 'In Progress'], 'Material Pending': ['In Progress', 'Completed'], 'Estimate Awaiting Approval': ['Material Pending', 'In Progress']}
        if not can_work(request.user, booking): raise PermissionDenied()
        if target not in allowed.get(booking.status, []): raise ValidationError('Invalid status transition.')
        if target in ['Confirmed', 'Assigned', 'Cancelled'] and not is_staff(request.user): raise PermissionDenied()
        booking.status = target
        if target == 'Completed':
            if EstimateLine.objects.filter(estimate__booking=booking, reserved=True, issued=False).exists(): raise ValidationError('Issue or release reserved materials first.')
            booking.completed_at = timezone.now()
        booking.save(update_fields=['status', 'completed_at', 'updated_at'])
        log(booking, request.user, f'Status changed to {target}')
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=['post'])
    def update_work(self, request, pk=None):
        booking = self.get_object()
        if not can_work(request.user, booking): raise PermissionDenied()
        for field in ['diagnosis', 'job_notes', 'labour_charge']:
            if field in request.data: setattr(booking, field, request.data[field])
        booking.full_clean(exclude=['photo'])
        booking.save()
        log(booking, request.user, 'Work details updated')
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=['post'])
    def request_change(self, request, pk=None):
        booking = self.get_object()
        if booking.customer_id != request.user.id or booking.status in ['Completed', 'Cancelled']: raise PermissionDenied()
        if request.data.get('cancellation_request'):
            booking.cancellation_request = request.data['cancellation_request']
            log(booking, request.user, 'Cancellation requested')
        elif request.data.get('reschedule_request'):
            booking.reschedule_request = request.data['reschedule_request']
            log(booking, request.user, 'Reschedule requested')
        else: raise ValidationError('Provide a cancellation or reschedule request.')
        booking.full_clean(exclude=['photo']); booking.save()
        return Response(self.get_serializer(booking).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        if not is_staff(request.user): raise PermissionDenied()
        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(pk=pk)
            if booking.status in ['Completed', 'Cancelled'] or EstimateLine.objects.filter(estimate__booking=booking, issued=True).exists():
                raise ValidationError('This job cannot be cancelled after completion or material issue.')
            release_reservations(booking, request.user)
            booking.status = 'Cancelled'; booking.save(update_fields=['status'])
            log(booking, request.user, 'Booking cancelled by staff')
        return Response(self.get_serializer(booking).data)

class EstimateViewSet(viewsets.ModelViewSet):
    serializer_class = EstimateSerializer
    queryset = Estimate.objects.all()
    http_method_names = ['get', 'post', 'head', 'options']
    def get_queryset(self):
        q = Estimate.objects.select_related('booking').prefetch_related('lines__product')
        if is_staff(self.request.user): return q
        if is_technician(self.request.user): return q.filter(booking__technician=self.request.user)
        return q.filter(booking__customer=self.request.user)
    def create(self, request):
        booking = Booking.objects.filter(pk=request.data.get('booking')).first()
        if not booking or not (can_work(request.user, booking) or (booking.customer_id == request.user.id and not booking.estimates.exists())): raise PermissionDenied()
        if booking.mode != 'with_materials': raise ValidationError('This booking is service only.')
        lines = request.data.get('lines')
        if not isinstance(lines, list) or not lines: raise ValidationError('Add at least one material.')
        with transaction.atomic():
            estimate = Estimate.objects.create(booking=booking, note=request.data.get('note', ''))
            for row in lines:
                product = Product.objects.filter(pk=row.get('product'), active=True).first()
                try: quantity = int(row.get('quantity', 0))
                except (TypeError, ValueError): quantity = 0
                if not product or quantity < 1: raise ValidationError('Invalid product or quantity.')
                EstimateLine.objects.create(estimate=estimate, product=product, quantity=quantity, unit_price=product.price, tax_rate=product.tax_rate)
            log(booking, request.user, 'Material estimate drafted')
        return Response(self.get_serializer(estimate).data, status=201)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        estimate = self.get_object()
        if not can_work(request.user, estimate.booking) or estimate.status != 'draft': raise PermissionDenied()
        estimate.status = 'sent'; estimate.save(update_fields=['status'])
        estimate.booking.status = 'Estimate Awaiting Approval'; estimate.booking.save(update_fields=['status'])
        log(estimate.booking, request.user, 'Estimate sent for customer approval')
        return Response(self.get_serializer(estimate).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        with transaction.atomic():
            estimate = Estimate.objects.select_for_update().select_related('booking').get(pk=pk)
            if estimate.booking.customer_id != request.user.id: raise PermissionDenied()
            if estimate.status != 'sent': raise ValidationError('Estimate is not awaiting approval.')
            for line in estimate.lines.select_related('product'):
                product = Product.objects.select_for_update().get(pk=line.product_id)
                if product.available < line.quantity: raise ValidationError(f'Insufficient stock for {product.name}.')
                product.reserved += line.quantity; product.save(update_fields=['reserved'])
                line.reserved = True; line.save(update_fields=['reserved'])
                StockMovement.objects.create(product=product, booking=estimate.booking, kind='reserve', quantity=line.quantity, actor=request.user)
            estimate.status = 'approved'; estimate.save(update_fields=['status'])
            estimate.booking.status = 'Material Pending'; estimate.booking.save(update_fields=['status'])
            log(estimate.booking, request.user, 'Estimate approved; materials reserved')
        return Response(self.get_serializer(estimate).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        estimate = self.get_object()
        if estimate.booking.customer_id != request.user.id or estimate.status != 'sent': raise PermissionDenied()
        estimate.status = 'rejected'; estimate.save(update_fields=['status'])
        estimate.booking.status = 'In Progress'; estimate.booking.save(update_fields=['status'])
        log(estimate.booking, request.user, 'Estimate rejected')
        return Response(self.get_serializer(estimate).data)

    @action(detail=True, methods=['post'])
    def issue(self, request, pk=None):
        with transaction.atomic():
            estimate = Estimate.objects.select_for_update().select_related('booking').get(pk=pk)
            if not can_work(request.user, estimate.booking): raise PermissionDenied()
            if estimate.status != 'approved': raise ValidationError('Estimate is not approved.')
            for line in estimate.lines.select_related('product'):
                if line.issued: continue
                product = Product.objects.select_for_update().get(pk=line.product_id)
                if not line.reserved or product.stock < line.quantity: raise ValidationError('Material reservation is invalid.')
                product.stock -= line.quantity; product.reserved -= line.quantity
                product.save(update_fields=['stock', 'reserved'])
                line.issued = True; line.reserved = False; line.save(update_fields=['issued', 'reserved'])
                StockMovement.objects.create(product=product, booking=estimate.booking, kind='issue', quantity=-line.quantity, actor=request.user)
            estimate.booking.status = 'In Progress'; estimate.booking.save(update_fields=['status'])
            log(estimate.booking, request.user, 'Materials issued')
        return Response(self.get_serializer(estimate).data)

class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockMovementSerializer
    queryset = StockMovement.objects.all()
    def get_queryset(self):
        if not is_staff(self.request.user): raise PermissionDenied()
        return StockMovement.objects.order_by('-created_at')
    @action(detail=False, methods=['post'])
    def record(self, request):
        if not is_staff(request.user): raise PermissionDenied()
        kind = request.data.get('kind')
        if kind not in ['purchase', 'return', 'adjust']: raise ValidationError('Use purchase, return or adjust.')
        try: quantity = int(request.data.get('quantity'))
        except (TypeError, ValueError): raise ValidationError('Enter a whole-number quantity.')
        if kind != 'adjust' and quantity <= 0: raise ValidationError('Quantity must be positive.')
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=request.data.get('product'))
            if product.stock + quantity < product.reserved: raise ValidationError('Cannot reduce below reserved stock.')
            product.stock += quantity; product.save(update_fields=['stock'])
            movement = StockMovement.objects.create(product=product, kind=kind, quantity=quantity, note=request.data.get('note', ''), actor=request.user)
        return Response(self.get_serializer(movement).data, status=201)

class JobPhotoViewSet(viewsets.ModelViewSet):
    serializer_class = JobPhotoSerializer
    queryset = JobPhoto.objects.all()
    http_method_names = ['get', 'post', 'head', 'options']
    def get_queryset(self):
        q = JobPhoto.objects.select_related('booking')
        if is_staff(self.request.user): return q
        if is_technician(self.request.user): return q.filter(booking__technician=self.request.user)
        return q.filter(booking__customer=self.request.user)
    def perform_create(self, serializer):
        booking = serializer.validated_data['booking']
        if not can_work(self.request.user, booking): raise PermissionDenied()
        serializer.save(uploaded_by=self.request.user)
        log(booking, self.request.user, 'Job photo added')

class FeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = FeedbackSerializer
    queryset = Feedback.objects.all()
    http_method_names = ['get', 'post', 'head', 'options']
    def get_queryset(self):
        return Feedback.objects.all() if is_staff(self.request.user) else Feedback.objects.filter(booking__customer=self.request.user)
    def perform_create(self, serializer):
        booking = serializer.validated_data['booking']
        if booking.customer_id != self.request.user.id or booking.status != 'Completed': raise PermissionDenied()
        serializer.save()

class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all()
    def get_queryset(self):
        q = Invoice.objects.select_related('booking')
        if is_staff(self.request.user): return q
        return q.filter(booking__customer=self.request.user)
    @action(detail=False, methods=['post'])
    def generate(self, request):
        if not is_staff(request.user): raise PermissionDenied()
        booking = Booking.objects.get(pk=request.data.get('booking'))
        if booking.status != 'Completed': raise ValidationError('Complete the job first.')
        invoice, _ = Invoice.objects.get_or_create(booking=booking)
        return Response(self.get_serializer(invoice).data)
    @action(detail=True, methods=['post'])
    def record_payment(self, request, pk=None):
        if not is_staff(request.user): raise PermissionDenied()
        invoice = self.get_object()
        method = request.data.get('payment_method')
        if method not in ['cash', 'pay_after_service']: raise ValidationError('Only cash and pay after service are supported.')
        invoice.payment_method = method
        invoice.paid_at = timezone.now() if method == 'cash' else None
        invoice.save(update_fields=['payment_method', 'paid_at'])
        return Response(self.get_serializer(invoice).data)

@extend_schema(responses=inline_serializer(name='DashboardSummary', fields={'bookings': rf_serializers.IntegerField(), 'active': rf_serializers.IntegerField(), 'completed': rf_serializers.IntegerField(), 'cancelled': rf_serializers.IntegerField(), 'stock_value': rf_serializers.DecimalField(max_digits=12, decimal_places=2), 'revenue_cash': rf_serializers.DecimalField(max_digits=12, decimal_places=2)}))
@api_view(['GET'])
def dashboard(request):
    if not is_staff(request.user): raise PermissionDenied()
    bookings = Booking.objects.all()
    return Response({'bookings': bookings.count(), 'active': bookings.exclude(status__in=['Completed', 'Cancelled']).count(), 'completed': bookings.filter(status='Completed').count(), 'cancelled': bookings.filter(status='Cancelled').count(), 'by_status': list(bookings.values('status').annotate(count=Count('id'))), 'by_service': list(bookings.values('service__category').annotate(count=Count('id'))), 'technician_workload': list(bookings.exclude(technician=None).exclude(status__in=['Completed', 'Cancelled']).values('technician__username').annotate(count=Count('id'))), 'stock_value': sum(p.price * p.stock for p in Product.objects.all()), 'low_stock': list(Product.objects.filter(stock__lte=F('minimum_stock')).values('id', 'name', 'sku', 'stock')), 'revenue_cash': sum((i.booking.labour_charge or i.booking.service.labour_price) + i.booking.service.visit_price for i in Invoice.objects.filter(payment_method='cash'))})

@extend_schema(responses=inline_serializer(name='TechnicianList', fields={'id': rf_serializers.IntegerField(), 'username': rf_serializers.CharField(), 'first_name': rf_serializers.CharField(), 'last_name': rf_serializers.CharField()}, many=True))
@api_view(['GET'])
def technicians(request):
    if not is_staff(request.user): raise PermissionDenied()
    from django.contrib.auth.models import User
    return Response(list(User.objects.filter(profile__role='technician', is_active=True).values('id', 'username', 'first_name', 'last_name')))
