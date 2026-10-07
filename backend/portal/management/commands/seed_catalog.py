import json
from decimal import Decimal
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from portal.models import Service, ServiceArea, Product

CATALOG_ROOT = Path(__file__).resolve().parents[4] / 'catalog'
SERVICES = [
    ('electrical', 'Fan installation and replacement', 499, 199, 'Fan installation, replacement or troubleshooting. Final scope and charges are confirmed before work.'),
    ('electrical', 'Switch and socket repair', 349, 199, 'Switchboard, switch or socket fault diagnosis and repair. Extra wiring or materials are quoted before work.'),
    ('electrical', 'DB and MCB inspection', 799, 299, 'Inspection of distribution board, MCBs and related electrical protection. Rectification is quoted after inspection.'),
    ('networking', 'Wi-Fi router setup', 599, 199, 'Router setup and basic Wi-Fi configuration. Additional hardware or cabling is quoted separately.'),
    ('networking', 'LAN point installation', 699, 249, 'LAN point installation at an agreed location. Cable length, conduit and hardware are confirmed in the estimate.'),
    ('networking', 'Structured cabling inspection', 999, 299, 'Inspection of office or building structured cabling with findings and recommended next steps.'),
    ('cctv', 'CCTV camera installation', 899, 299, 'Camera mounting and setup. Cabling, storage and additional hardware are confirmed before installation.'),
    ('cctv', 'DVR / NVR setup', 799, 299, 'DVR/NVR configuration and basic recording or remote-viewing setup, subject to compatible equipment and network access.'),
    ('cctv', 'CCTV system maintenance', 999, 299, 'Inspection and maintenance of CCTV system components. Replacement parts are quoted separately.'),
]
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
    help = 'Create the neutral service and product catalogue without user credentials or unverified promotional claims.'

    def handle(self, *args, **options):
        tax_rate = Decimal(str(settings.DEFAULT_TAX_RATE))
        seeded_services = []
        for category, name, labour, visit, description in SERVICES:
            service, created = Service.objects.get_or_create(
                category=category,
                name=name,
                defaults={'labour_price': labour, 'visit_price': visit, 'tax_rate': tax_rate, 'description': description},
            )
            if created:
                self.stdout.write(f'Created service: {name}')
            seeded_services.append(service)

        for item in json.loads(CATALOG.read_text(encoding='utf-8')):
            sku = LEGACY_SKUS.get(item['id'], item['id'].upper())
            product, created = Product.objects.get_or_create(sku=sku, defaults={
                'name': f"{item['brand']} {item['title']}",
                'category': item['category'],
                'brand': item['brand'],
                'description': ' '.join(item.get('specs', [])),
                'unit': item.get('unit', 'piece'),
                'price': item['price'],
                'tax_rate': tax_rate,
                'stock': 0,
                'reserved': 0,
                'minimum_stock': 1,
                'image_url': 'https://sachinranafiit-eng.github.io/shiva.github.io/' + item['image'],
            })
            if not created and sku in LEGACY_DEFAULT_PRICES and product.price == LEGACY_DEFAULT_PRICES[sku]:
                product.price = item['price']
                product.save(update_fields=['price'])

        area, _ = ServiceArea.objects.get_or_create(name='Dehradun', city='Dehradun', postal_code='')
        area.services.add(*seeded_services)
        self.stdout.write(self.style.SUCCESS('Service and material catalogue ready. Confirm tax rates in admin before billing if tax is legally applicable.'))
