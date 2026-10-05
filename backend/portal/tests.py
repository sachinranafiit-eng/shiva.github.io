from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from PIL import Image
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from .models import Address, Booking, Estimate, Offer, Product, Profile, Service, ServiceArea, AvailabilitySlot, StockMovement, JobPhoto, Invoice
from .serializers import InvoiceSerializer
from .management.commands.seed_catalog import MATCHED_RATES

class ComparableRateTests(TestCase):
    def test_shared_catalog_starts_without_claiming_unverified_stock(self):
        call_command('seed_catalog', verbosity=0)
        self.assertEqual(Product.objects.count(), 45)
        self.assertEqual(StockMovement.objects.count(), 0)
        camera = Product.objects.get(sku='CP-DOME-2MP')
        self.assertEqual(camera.price, Decimal('2500'))
        self.assertEqual(camera.available, 0)
        camera.price = Decimal('2600')
        camera.stock = 3
        camera.save(update_fields=['price', 'stock'])
        call_command('seed_catalog', verbosity=0)
        camera.refresh_from_db()
        self.assertEqual(Product.objects.count(), 45)
        self.assertEqual(camera.price, Decimal('2600'))
        self.assertEqual(camera.stock, 3)

    def test_legacy_roll_stock_is_not_relabelled_as_metres(self):
        roll = Product.objects.create(sku='MOL-CAT6', name='Molex Cat6 cable', category='Networking', unit='roll', price=6999, stock=4)
        call_command('seed_catalog', verbosity=0)
        roll.refresh_from_db()
        self.assertEqual(roll.unit, 'roll')
        self.assertEqual(roll.stock, 4)
        self.assertTrue(Product.objects.filter(sku='MOLEX-CAT6-CABLE', unit='meter', stock=0).exists())

    def test_matched_starting_totals_stay_at_least_five_percent_lower(self):
        call_command('seed_catalog', verbosity=0)
        for category, name, _, urban_company_price, _ in MATCHED_RATES:
            service = Service.objects.get(category=category, name=name)
            total = (service.labour_price + service.visit_price) * (Decimal('1') + service.tax_rate / 100)
            self.assertEqual(service.visit_price, 0)
            self.assertLessEqual(total, Decimal(urban_company_price) * Decimal('0.95'), name)
        service.labour_price = Decimal('123.45')
        service.save(update_fields=['labour_price'])
        call_command('seed_catalog', verbosity=0)
        service.refresh_from_db()
        self.assertEqual(service.labour_price, Decimal('123.45'))

class PortalFlowTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user('customer')
        self.other = User.objects.create_user('other')
        self.tech = User.objects.create_user('tech')
        self.staff = User.objects.create_user('staff', is_staff=True)
        Profile.objects.create(user=self.customer)
        Profile.objects.create(user=self.other)
        Profile.objects.create(user=self.tech, role='technician')
        Profile.objects.create(user=self.staff, role='staff')
        self.address = Address.objects.create(user=self.customer, label='Home', line='Doon Road', postal_code='248001')
        self.service = Service.objects.create(name='Camera installation', category='cctv', labour_price=500, visit_price=100)
        self.product = Product.objects.create(sku='CAM-1', name='Camera', category='CCTV', price=1200, stock=2)
        self.booking = Booking.objects.create(customer=self.customer, service=self.service, address=self.address, issue='Install a camera outside', preferred_at=timezone.now() + timedelta(days=2), mode='with_materials', technician=self.tech, status='In Progress')

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.get_or_create(user=user)[0].key}')

    def test_customer_cannot_see_other_booking_or_use_other_address(self):
        self.auth(self.other)
        self.assertEqual(self.client.get('/api/bookings/').data['count'], 0)
        self.assertEqual(self.client.get(f'/api/bookings/{self.booking.id}/').status_code, 404)
        response = self.client.post('/api/bookings/', {'service': self.service.id, 'address': self.address.id, 'issue': 'Fix the camera wiring', 'preferred_at': (timezone.now() + timedelta(days=1)).isoformat(), 'mode': 'service_only'})
        self.assertEqual(response.status_code, 400)

    def test_technician_only_assigned_and_valid_transitions(self):
        other_booking = Booking.objects.create(customer=self.other, service=self.service, address=Address.objects.create(user=self.other, label='Office', line='Rajpur Road', postal_code='248001'), issue='Repair camera', preferred_at=timezone.now() + timedelta(days=2), mode='service_only')
        self.auth(self.tech)
        self.assertEqual(self.client.get('/api/bookings/').data['count'], 1)
        self.assertEqual(self.client.get(f'/api/bookings/{other_booking.id}/').status_code, 404)
        bad = self.client.post(f'/api/bookings/{self.booking.id}/transition/', {'status': 'Assigned'})
        self.assertEqual(bad.status_code, 400)
        good = self.client.post(f'/api/bookings/{self.booking.id}/transition/', {'status': 'Inspection Required'})
        self.assertEqual(good.status_code, 200)

    def test_estimate_approval_reserves_once_and_issue_moves_stock(self):
        self.auth(self.tech)
        created = self.client.post('/api/estimates/', {'booking': self.booking.id, 'lines': [{'product': self.product.id, 'quantity': 2}]}, format='json')
        self.assertEqual(created.status_code, 201)
        estimate_id = created.data['id']
        self.assertEqual(self.client.post(f'/api/estimates/{estimate_id}/send/').status_code, 200)
        self.auth(self.other)
        self.assertEqual(self.client.post(f'/api/estimates/{estimate_id}/approve/').status_code, 403)
        self.auth(self.customer)
        self.assertEqual(self.client.post(f'/api/estimates/{estimate_id}/approve/').status_code, 200)
        self.product.refresh_from_db(); self.assertEqual((self.product.stock, self.product.reserved), (2, 2))
        self.assertEqual(self.client.post(f'/api/estimates/{estimate_id}/approve/').status_code, 400)
        self.auth(self.tech)
        self.assertEqual(self.client.post(f'/api/estimates/{estimate_id}/issue/').status_code, 200)
        self.product.refresh_from_db(); self.assertEqual((self.product.stock, self.product.reserved), (0, 0))
        self.assertEqual(StockMovement.objects.filter(product=self.product, kind='issue').count(), 1)
        self.assertEqual(self.client.post(f'/api/estimates/{estimate_id}/issue/').status_code, 200)
        self.assertEqual(StockMovement.objects.filter(product=self.product, kind='issue').count(), 1)

    def test_insufficient_stock_rolls_back_reservation(self):
        self.auth(self.tech)
        created = self.client.post('/api/estimates/', {'booking': self.booking.id, 'lines': [{'product': self.product.id, 'quantity': 3}]}, format='json')
        self.assertEqual(created.status_code, 201)
        self.client.post(f"/api/estimates/{created.data['id']}/send/")
        self.auth(self.customer)
        self.assertEqual(self.client.post(f"/api/estimates/{created.data['id']}/approve/").status_code, 400)
        self.product.refresh_from_db(); self.assertEqual(self.product.reserved, 0)
        self.assertEqual(Estimate.objects.get(pk=created.data['id']).status, 'sent')

    def test_staff_stock_purchase_and_customer_denial(self):
        self.auth(self.customer)
        self.assertEqual(self.client.post('/api/stock-movements/record/', {'product': self.product.id, 'kind': 'purchase', 'quantity': 2}).status_code, 403)
        self.auth(self.staff)
        self.assertEqual(self.client.post('/api/stock-movements/record/', {'product': self.product.id, 'kind': 'purchase', 'quantity': 2}).status_code, 201)
        self.product.refresh_from_db(); self.assertEqual(self.product.stock, 4)

    def test_offer_applies_to_quoted_labour_and_invoice(self):
        offer = Offer.objects.create(code='SAVE10', title='Labour discount', discount_type='percent', value=10, starts_at=timezone.now() - timedelta(days=1), ends_at=timezone.now() + timedelta(days=1))
        self.auth(self.customer)
        response = self.client.post('/api/bookings/', {'service': self.service.id, 'offer': offer.id, 'address': self.address.id, 'issue': 'Install camera in entrance', 'preferred_at': (timezone.now() + timedelta(days=1)).isoformat(), 'mode': 'service_only'})
        self.assertEqual(response.status_code, 201)
        booking = Booking.objects.get(pk=response.data['id'])
        self.assertEqual(booking.labour_quoted, Decimal('500'))
        self.service.labour_price = 900; self.service.save()
        offer.value = 50; offer.save()
        charges = InvoiceSerializer(Invoice.objects.create(booking=booking)).data['charges']
        self.assertEqual(Decimal(charges['discount']), Decimal('50'))
        self.assertEqual(Decimal(charges['total']), Decimal('649'))

    def test_only_assigned_technician_can_upload_job_photo(self):
        def photo():
            data = BytesIO(); Image.new('RGB', (2, 2), 'blue').save(data, format='PNG')
            return SimpleUploadedFile('job.png', data.getvalue(), content_type='image/png')
        self.auth(self.other)
        self.assertEqual(self.client.post('/api/job-photos/', {'booking': self.booking.id, 'image': photo()}, format='multipart').status_code, 403)
        self.auth(self.tech)
        self.assertEqual(self.client.post('/api/job-photos/', {'booking': self.booking.id, 'image': photo(), 'caption': 'Installed'}, format='multipart').status_code, 201)
        self.assertEqual(JobPhoto.objects.filter(booking=self.booking).count(), 1)

    def test_service_area_restricts_booking_location(self):
        area = ServiceArea.objects.create(name='Dehradun', city='Dehradun')
        area.services.add(self.service)
        self.auth(self.other)
        outside = Address.objects.create(user=self.other, label='Other city', line='Test lane', city='Haridwar', postal_code='249401')
        response = self.client.post('/api/bookings/', {'service': self.service.id, 'address': outside.id, 'issue': 'Install one security camera', 'preferred_at': (timezone.now() + timedelta(days=1)).isoformat(), 'mode': 'service_only'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(f'/api/services/?area={area.id}').data['count'], 1)

    def test_published_slot_capacity_is_enforced(self):
        start = timezone.now() + timedelta(days=3)
        slot = AvailabilitySlot.objects.create(service=self.service, starts_at=start, ends_at=start + timedelta(hours=2), capacity=1)
        self.auth(self.customer)
        data = {'service': self.service.id, 'address': self.address.id, 'issue': 'Install front door camera', 'preferred_at': start.isoformat(), 'mode': 'service_only'}
        self.assertEqual(self.client.post('/api/bookings/', data).status_code, 201)
        self.assertEqual(self.client.post('/api/bookings/', data).status_code, 400)
        self.assertEqual(self.client.get(f'/api/availability/?service={self.service.id}').data['results'][0]['remaining'], 0)
