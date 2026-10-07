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

class CatalogSeedTests(TestCase):
    def test_shared_catalog_starts_without_claiming_stock_or_tax(self):
        call_command('seed_catalog', verbosity=0)
        self.assertEqual(Product.objects.count(), 45)
        self.assertEqual(Service.objects.count(), 9)
        self.assertEqual(StockMovement.objects.count(), 0)
        camera = Product.objects.get(sku='CP-DOME-2MP')
        self.assertEqual(camera.price, Decimal('2500'))
        self.assertEqual(camera.available, 0)
        self.assertEqual(camera.tax_rate, Decimal('0'))
        self.assertFalse(Service.objects.filter(description__icontains='Urban Company').exists())
        self.assertFalse(Service.objects.filter(description__icontains='5%').exists())
        self.assertTrue(all(s.tax_rate == 0 for s in Service.objects.all()))

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
        self.assertEqual(Decimal(charges['total']), Decimal('550'))

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

class ProductionReadinessFlowTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user('ops', password='OpsPass!2026', is_staff=True)
        self.tech = User.objects.create_user('fieldtech', password='TechPass!2026')
        Profile.objects.create(user=self.staff, role='staff', phone='9259599151')
        Profile.objects.create(user=self.tech, role='technician', phone='9876543210')
        self.service = Service.objects.create(name='Electrical inspection', category='electrical', labour_price=500, visit_price=100, tax_rate=0)
        area = ServiceArea.objects.create(name='Dehradun', city='Dehradun')
        area.services.add(self.service)

    def auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.get_or_create(user=user)[0].key}')

    def test_health_endpoint_is_public(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'ok')

    def test_registration_requires_contact_phone(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'no-phone',
            'first_name': 'Test',
            'email': 'nophone@example.com',
            'password': 'StrongPass!2026',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('phone', response.data)

    def test_customer_to_admin_to_technician_to_invoice_flow(self):
        register = self.client.post('/api/auth/register/', {
            'username': 'realcustomer',
            'first_name': 'Ravi',
            'last_name': 'Kumar',
            'email': 'ravi@example.com',
            'phone': '+91 98100 12345',
            'password': 'StrongPass!2026',
        }, format='json')
        self.assertEqual(register.status_code, 201)
        token = register.data['token']
        self.assertEqual(register.data['user']['phone'], '+919810012345')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        address = self.client.post('/api/addresses/', {
            'label': 'Home', 'line': 'Rajpur Road', 'city': 'Dehradun', 'postal_code': '248001'
        }, format='json')
        self.assertEqual(address.status_code, 201)

        booking = self.client.post('/api/bookings/', {
            'service': self.service.id,
            'address': address.data['id'],
            'issue': 'Please inspect intermittent power tripping in the house.',
            'preferred_at': (timezone.now() + timedelta(days=2)).isoformat(),
            'mode': 'service_only',
            'urgency': 'standard',
        }, format='json')
        self.assertEqual(booking.status_code, 201)
        booking_id = booking.data['id']

        self.auth(self.staff)
        dashboard = self.client.get('/api/dashboard/')
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data['bookings'], 1)
        assigned = self.client.post(f'/api/bookings/{booking_id}/assign/', {'technician': self.tech.id}, format='json')
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.data['status'], 'Assigned')

        self.auth(self.tech)
        self.assertEqual(self.client.post(f'/api/bookings/{booking_id}/transition/', {'status': 'Accepted'}, format='json').status_code, 200)
        self.assertEqual(self.client.post(f'/api/bookings/{booking_id}/transition/', {'status': 'In Progress'}, format='json').status_code, 200)
        work = self.client.post(f'/api/bookings/{booking_id}/update_work/', {
            'diagnosis': 'Loose termination found in the distribution board.',
            'job_notes': 'Termination corrected and circuit checked.',
            'labour_charge': '600.00',
        }, format='json')
        self.assertEqual(work.status_code, 200)
        complete = self.client.post(f'/api/bookings/{booking_id}/transition/', {'status': 'Completed'}, format='json')
        self.assertEqual(complete.status_code, 200)

        self.auth(self.staff)
        invoice = self.client.post('/api/invoices/generate/', {'booking': booking_id}, format='json')
        self.assertEqual(invoice.status_code, 200)
        self.assertEqual(Decimal(invoice.data['charges']['total']), Decimal('700'))
        paid = self.client.post(f"/api/invoices/{invoice.data['id']}/record_payment/", {'payment_method': 'cash'}, format='json')
        self.assertEqual(paid.status_code, 200)

        customer = User.objects.get(username='realcustomer')
        self.auth(customer)
        feedback = self.client.post('/api/feedback/', {'booking': booking_id, 'rating': 5, 'comment': 'Work completed.'}, format='json')
        self.assertEqual(feedback.status_code, 201)
