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
# Comparable public Urban Company Dehradun starting prices checked 2026-10-03.
# Labour is stored before 18% tax, with no extra visit charge. The customer-facing
# starting total after tax is 5% below the matching published UC price.
MATCHED_RATES = [
    ('electrical', 'Regular ceiling fan installation', '71.65', 89, 'One regular ceiling fan installed at an existing point.'),
    ('electrical', 'Switch replacement or installation', '39.44', 49, 'One standard switch at an existing point.'),
    ('electrical', 'Socket replacement or installation', '47.50', 59, 'One standard socket at an existing point.'),
    ('electrical', 'Tube light replacement or installation', '63.60', 79, 'One tube light at an existing point.'),
    ('electrical', 'MCB or fuse replacement', '95.80', 119, 'One MCB or fuse at an existing board.'),
    ('cctv', 'Wireless CCTV camera installation', '200.46', 249, 'One wireless camera installation and basic connection at an existing power point.'),
]
SCOPED_DESCRIPTIONS = {
    'Fan installation and replacement': 'Complex fan installation, replacement or troubleshooting beyond a standard existing-point fit. Scope and final charges are confirmed before work.',
    'Switch and socket repair': 'Switchboard fault diagnosis or multi-point repair. For a single basic switch or socket at an existing point, choose the lower-priced replacement service.',
    'CCTV camera installation': 'Wired camera mounting and cabling. For one wireless camera at an existing power point, choose the lower-priced wireless installation service.',
}
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
            legacy_description = f'Professional {name.lower()} in Dehradun. Final scope is confirmed after inspection.'
            service, created = Service.objects.get_or_create(category=category, name=name, defaults={'labour_price': labour, 'visit_price': visit, 'description': SCOPED_DESCRIPTIONS.get(name, legacy_description)})
            if not created and name in SCOPED_DESCRIPTIONS and service.description == legacy_description:
                service.description = SCOPED_DESCRIPTIONS[name]
                service.save(update_fields=['description'])
        for category, name, labour, source_price, scope in MATCHED_RATES:
            Service.objects.get_or_create(category=category, name=name, defaults={
                'labour_price': labour, 'visit_price': 0, 'tax_rate': 18,
                'description': f'{scope} Materials are extra. Starting total including 18% tax is 5% below Urban Company Dehradun’s listed ₹{source_price} price as checked 3 October 2026. Extra scope is quoted before work.',
            })
        for sku, name, category, brand, price, stock, image in PRODUCTS:
            product, created = Product.objects.get_or_create(sku=sku, defaults={'name': name, 'category': category, 'brand': brand, 'price': price, 'stock': stock, 'minimum_stock': 3, 'image_url': SITE + image})
            if created:
                StockMovement.objects.create(product=product, kind='purchase', quantity=stock, note='Initial sample catalogue stock')
        area, created = ServiceArea.objects.get_or_create(name='Dehradun', city='Dehradun', postal_code='')
        if created:
            area.services.set(Service.objects.all())
        else:
            area.services.add(*Service.objects.filter(name__in=[item[1] for item in MATCHED_RATES]))
        self.stdout.write(self.style.SUCCESS('Sample service and material catalogue ready.'))
