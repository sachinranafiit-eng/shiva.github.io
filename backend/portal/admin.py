from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile, Address, Service, ServiceArea, AvailabilitySlot, Offer, Product, Booking, Estimate, EstimateLine, StockMovement, Activity, JobPhoto, Invoice, Feedback

admin.site.site_header = 'Shiva Enterprises Super Admin'
admin.site.site_title = 'Shiva Enterprises'
admin.site.index_title = 'Services, bookings, materials and offers'

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 1

admin.site.unregister(User)
@admin.register(User)
class PortalUserAdmin(UserAdmin):
    inlines = [ProfileInline]

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'label', 'city', 'postal_code')
    search_fields = ('user__username', 'line', 'city', 'postal_code')
    list_filter = ('city',)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'labour_price', 'visit_price', 'tax_rate', 'active')
    list_editable = ('labour_price', 'visit_price', 'active')
    list_filter = ('category', 'active')
    search_fields = ('name', 'description')
    fieldsets = ((None, {'fields': ('name', 'category', 'description', 'active')}), ('Rates and tax', {'fields': ('labour_price', 'visit_price', 'tax_rate')}), ('Service photo', {'fields': ('image', 'image_url')}))

@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'postal_code', 'active')
    list_filter = ('city', 'active')
    search_fields = ('name', 'city', 'postal_code')
    filter_horizontal = ('services',)

@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ('service', 'starts_at', 'ends_at', 'capacity', 'active')
    list_filter = ('service__category', 'active')
    search_fields = ('service__name',)

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'service', 'discount_type', 'value', 'starts_at', 'ends_at', 'active')
    list_editable = ('active',)
    list_filter = ('active', 'discount_type', 'service')
    search_fields = ('code', 'title', 'description')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'brand', 'price', 'stock', 'reserved', 'minimum_stock', 'active')
    list_editable = ('price', 'minimum_stock', 'active')
    list_filter = ('category', 'brand', 'active')
    search_fields = ('sku', 'name', 'brand')
    readonly_fields = ('stock', 'reserved')
    fieldsets = ((None, {'fields': ('sku', 'name', 'category', 'brand', 'description', 'unit', 'active')}), ('Pricing and inventory', {'fields': ('price', 'tax_rate', 'stock', 'reserved', 'minimum_stock')}), ('Product photo', {'fields': ('image', 'image_url')}))

class EstimateLineInline(admin.TabularInline):
    model = EstimateLine
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_price', 'tax_rate', 'reserved', 'issued')
    can_delete = False
    def has_add_permission(self, request, obj=None): return False

@admin.register(Estimate)
class EstimateAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    readonly_fields = ('booking', 'status', 'note', 'created_at')
    inlines = [EstimateLineInline]
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'service', 'status', 'technician', 'preferred_at', 'created_at')
    list_filter = ('status', 'service__category', 'urgency', 'mode')
    search_fields = ('customer__username', 'service__name', 'issue', 'address__line')
    readonly_fields = ('customer', 'service', 'offer', 'address', 'issue', 'preferred_at', 'urgency', 'mode', 'status', 'photo', 'labour_quoted', 'visit_quoted', 'tax_rate_quoted', 'offer_code_quoted', 'offer_discount_quoted', 'created_at', 'updated_at')
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    def save_model(self, request, obj, form, change):
        previous = Booking.objects.get(pk=obj.pk) if change else None
        super().save_model(request, obj, form, change)
        if previous and previous.technician_id != obj.technician_id:
            Activity.objects.create(booking=obj, actor=request.user, message=f'Technician changed to {obj.technician.username if obj.technician else "unassigned"}')

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'kind', 'quantity', 'booking', 'actor', 'created_at')
    list_filter = ('kind', 'created_at')
    search_fields = ('product__sku', 'product__name', 'note')
    readonly_fields = ('product', 'kind', 'quantity', 'booking', 'actor', 'created_at', 'note')
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('booking', 'actor', 'message', 'created_at')
    readonly_fields = ('booking', 'actor', 'message', 'created_at')
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(JobPhoto)
class JobPhotoAdmin(admin.ModelAdmin):
    list_display = ('booking', 'uploaded_by', 'caption', 'created_at')
    readonly_fields = ('booking', 'uploaded_by', 'image', 'caption', 'created_at')
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('booking', 'payment_method', 'paid_at', 'issued_at')
    list_filter = ('payment_method',)
    readonly_fields = ('booking', 'issued_at')
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('booking', 'rating', 'created_at')
    list_filter = ('rating',)
    readonly_fields = ('booking', 'rating', 'comment', 'created_at')
    def has_add_permission(self, request): return False
