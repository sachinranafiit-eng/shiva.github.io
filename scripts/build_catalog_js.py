"""Generate the marketing site's browser catalogue from the shared JSON file."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
products = json.loads((ROOT / 'catalog/products.json').read_text(encoding='utf-8'))
(ROOT / 'products.js').write_text(
    'window.SHIVA_CATALOG_PRODUCTS = ' + json.dumps(products, ensure_ascii=False, indent=2) + ';\n',
    encoding='utf-8',
)
