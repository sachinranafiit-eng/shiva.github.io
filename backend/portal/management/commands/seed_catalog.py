import json
from pathlib import Path
from django.core.management.base import BaseCommand
from portal.models import Service, ServiceArea, Product

CATALOG_ROOT = Path(__file__).resolve().parents[4] / 'catalog'
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
# Comparable public Urban Company Dehradun starting prices checked 2026-10-05.
# Labour is stored before 18% tax, with no extra visit charge. The customer-facing
# starting total after tax is 5% below the matching published UC price.
MATCHED_RATES = [
    (item['category'], item['name'], item['labour_price'], item['urban_company_price'], item['scope'])
    for item in json.loads((CATALOG_ROOT / 'comparable-services.json').read_text(encoding='utf-8'))
]
SCOPED_DESCRIPTIONS = {
    'Fan installation and replacement': 'Complex fan installation, replacement or troubleshooting beyond a standard existing-point fit. Scope and final charges are confirmed before work.',
    'Switch and socket repair': 'Switchboard fault diagnosis or multi-point repair. For a single basic switch or socket at an existing point, choose the lower-priced replacement service.',
    'CCTV camera installation': 'Wired camera mounting and cabling. For one wireless camera at an existing power point, choose the lower-priced wireless installation service.',
}
CATALOG = CATALOG_ROOT / 'products.json'
LEGACY_SKUS = {
    'schneider-acti9-mcb': 'SCH-MCB-1P',
    'anchor-roma-socket': 'ANC-SOCKET',
    'tp-link-archer-c6': 'TPL-ARCHER-C6',
    'cp-plus-2mp-dome': 'CP-DOME-2MP',
    'hikvision-2mp-bullet': 'HIK-BULLET-2MP',
}
LEGACY_DEFAULT_PRICES = {
    'SCH-MCB-1P': 650,
    'ANC-SOCKET': 190,
    'TPL-ARCHER-C6': 2499,
    'CP-DOME-2MP': 2199,
    'HIK-BULLET-2MP': 2399,
}

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
                'description': f'{scope} Materials are extra. Starting total including 18% tax is 5% below Urban Company Dehradun’s listed ₹{source_price} price as checked 5 October 2026. Extra scope is quoted before work.',
            })
        for item in json.loads(CATALOG.read_text(encoding='utf-8')):
            sku = LEGACY_SKUS.get(item['id'], item['id'].upper())
            product, created = Product.objects.get_or_create(sku=sku, defaults={
                'name': f"{item['brand']} {item['title']}",
                'category': item['category'], 'brand': item['brand'],
                'description': ' '.join(item.get('specs', [])),
                'unit': item.get('unit', 'piece'), 'price': item['price'],
                'stock': 0, 'reserved': 0, 'minimum_stock': 1,
                'image_url': 'https://sachinranafiit-eng.github.io/shiva.github.io/' + item['image'],
            })
            # The old demo prices were not based on the public catalogue. Align only
            # untouched defaults; preserve any staff price or stock adjustment.
            if not created and sku in LEGACY_DEFAULT_PRICES and product.price == LEGACY_DEFAULT_PRICES[sku]:
                product.price = item['price']
                product.save(update_fields=['price'])
        area, created = ServiceArea.objects.get_or_create(name='Dehradun', city='Dehradun', postal_code='')
        if created:
            area.services.set(Service.objects.all())
        else:
            area.services.add(*Service.objects.filter(name__in=[item[1] for item in MATCHED_RATES]))
        self.stdout.write(self.style.SUCCESS('Sample service and material catalogue ready.'))
