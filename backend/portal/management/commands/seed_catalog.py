from django.core.management.base import BaseCommand
from portal.models import Service, ServiceArea, Product, StockMovement

SITE = 'https://sachinranafiit-eng.github.io/shiva.github.io/assets/products/'
SERVICES = [
    ('electrical', 'Fan installation and replacement', 499, 199),
    ('electrical', 'Switch and socket repair', 349, 199),
    ('electrical', 'DB and MCB inspection', 799, 299),
    ('networking', 'Wi-Fi router setup', 599, 199),
    ('networking', 'LAN point installation', 699, 249),
    ('networking', 'Structured cabling inspection', 999, 299),
    ('cctv', 'CCTV camera installation', 899, 299),
    ('cctv', 'DVR / NVR setup', 799, 299),
    ('cctv', 'CCTV system maintenance', 999, 299),
]
PRODUCTS = [
    ('SCH-MCB-1P', 'Schneider Acti9 MCB', 'Electrical', 'Schneider', 650, 10, 'schneider-acti9-mcb.jpg'),
    ('POL-FR-WIRE', 'Polycab FR wire', 'Electrical', 'Polycab', 1250, 20, 'polycab-fr-wire.webp'),
    ('ANC-SOCKET', 'Anchor Roma socket', 'Electrical', 'Anchor', 190, 30, 'anchor-roma-socket.png'),
    ('TPL-ARCHER-C6', 'TP-Link Archer C6 router', 'Networking', 'TP-Link', 2499, 8, 'tp-link-archer-c6.jpg'),
    ('MOL-CAT6', 'Molex Cat6 cable', 'Networking', 'Molex', 6999, 4, 'molex-cat6-cable.webp'),
    ('CP-DOME-2MP', 'CP Plus 2MP dome camera', 'CCTV', 'CP Plus', 2199, 8, 'cp-plus-2mp-dome.png'),
    ('HIK-BULLET-2MP', 'Hikvision 2MP bullet camera', 'CCTV', 'Hikvision', 2399, 6, 'hikvision-2mp-bullet.png'),
]

class Command(BaseCommand):
    help = 'Create sample services and product catalogue without creating user credentials.'
    def handle(self, *args, **options):
        for category, name, labour, visit in SERVICES:
            Service.objects.get_or_create(category=category, name=name, defaults={'labour_price': labour, 'visit_price': visit, 'description': f'Professional {name.lower()} in Dehradun. Final scope is confirmed after inspection.'})
        for sku, name, category, brand, price, stock, image in PRODUCTS:
            product, created = Product.objects.get_or_create(sku=sku, defaults={'name': name, 'category': category, 'brand': brand, 'price': price, 'stock': stock, 'minimum_stock': 3, 'image_url': SITE + image})
            if created:
                StockMovement.objects.create(product=product, kind='purchase', quantity=stock, note='Initial sample catalogue stock')
        area, created = ServiceArea.objects.get_or_create(name='Dehradun', city='Dehradun', postal_code='')
        if created:
            area.services.set(Service.objects.all())
        self.stdout.write(self.style.SUCCESS('Sample service and material catalogue ready.'))
