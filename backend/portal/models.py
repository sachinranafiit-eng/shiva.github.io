from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models

MONEY = {'max_digits': 10, 'decimal_places': 2, 'default': 0}

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=12, choices=[('customer', 'Customer'), ('technician', 'Technician'), ('staff', 'Staff')], default='customer')
    phone = models.CharField(max_length=20, blank=True)

class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=60)
    line = models.CharField(max_length=255)
    city = models.CharField(max_length=80, default='Dehradun')
    postal_code = models.CharField(max_length=12)

class Service(models.Model):
    category = models.CharField(max_length=20, choices=[('electrical', 'Electrical'), ('networking', 'Networking'), ('cctv', 'CCTV')])
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    labour_price = models.DecimalField(**MONEY)
    visit_price = models.DecimalField(**MONEY)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='services/', blank=True)
    image_url = models.URLField(blank=True)

class ServiceArea(models.Model):
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=12, blank=True)
    services = models.ManyToManyField(Service, related_name='areas', blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.name} ({self.city})'

class AvailabilitySlot(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='availability_slots')
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    active = models.BooleanField(default=True)

    def clean(self):
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise ValidationError({'ends_at': 'End must be after start.'})

class Offer(models.Model):
    code = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    discount_type = models.CharField(max_length=10, choices=[('percent', 'Percent'), ('fixed', 'Fixed amount')])
    value = models.DecimalField(max_digits=8, decimal_places=2)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    active = models.BooleanField(default=True)

    def clean(self):
        if self.value <= 0 or (self.discount_type == 'percent' and self.value > 100):
            raise ValidationError({'value': 'Enter a positive discount, at most 100%.'})
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise ValidationError({'ends_at': 'End must be after start.'})

    def valid_for(self, service, now):
        return self.active and self.starts_at <= now <= self.ends_at and (self.service_id is None or self.service_id == service.id)

class Product(models.Model):
    sku = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=140)
    category = models.CharField(max_length=60)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20, default='piece')
    brand = models.CharField(max_length=80, blank=True)
    price = models.DecimalField(**MONEY)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    stock = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True)
    image_url = models.URLField(blank=True)
    active = models.BooleanField(default=True)

    @property
    def available(self):
        return self.stock - self.reserved

class Booking(models.Model):
    STATUSES = [(x, x) for x in ['New', 'Confirmed', 'Assigned', 'Accepted', 'In Progress', 'Inspection Required', 'Estimate Awaiting Approval', 'Material Pending', 'Completed', 'Cancelled']]
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='bookings')
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_bookings')
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    offer = models.ForeignKey(Offer, on_delete=models.SET_NULL, null=True, blank=True)
    offer_code_quoted = models.CharField(max_length=32, blank=True)
    offer_discount_quoted = models.DecimalField(**MONEY)
    labour_quoted = models.DecimalField(**MONEY)
    visit_quoted = models.DecimalField(**MONEY)
    tax_rate_quoted = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    address = models.ForeignKey(Address, on_delete=models.PROTECT)
    issue = models.TextField()
    preferred_at = models.DateTimeField()
    urgency = models.CharField(max_length=12, choices=[('standard', 'Standard'), ('urgent', 'Urgent')], default='standard')
    mode = models.CharField(max_length=20, choices=[('service_only', 'Service only'), ('with_materials', 'Service + materials')])
    status = models.CharField(max_length=32, choices=STATUSES, default='New')
    photo = models.ImageField(upload_to='bookings/', blank=True)
    diagnosis = models.TextField(blank=True)
    job_notes = models.TextField(blank=True)
    labour_charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cancellation_request = models.TextField(blank=True)
    reschedule_request = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Estimate(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='estimates')
    status = models.CharField(max_length=12, choices=[('draft', 'Draft'), ('sent', 'Sent'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='draft')
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class EstimateLine(models.Model):
    estimate = models.ForeignKey(Estimate, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(**MONEY)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    reserved = models.BooleanField(default=False)
    issued = models.BooleanField(default=False)

class StockMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='movements')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=12, choices=[('purchase', 'Purchase'), ('reserve', 'Reserve'), ('release', 'Release'), ('issue', 'Issue'), ('return', 'Return'), ('adjust', 'Adjust')])
    quantity = models.IntegerField()
    note = models.CharField(max_length=255, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Activity(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='activity')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

class JobPhoto(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='job_photos')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    image = models.ImageField(upload_to='job_updates/')
    caption = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Invoice(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name='invoice')
    issued_at = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=[('unpaid', 'Unpaid'), ('cash', 'Cash'), ('pay_after_service', 'Pay after service')], default='unpaid')
    paid_at = models.DateTimeField(null=True, blank=True)

class Feedback(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='feedback')
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
