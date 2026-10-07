# Generated for production readiness on 2026-10-07
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('portal', '0006_availabilityslot')]
    operations = [
        migrations.AlterField(model_name='service', name='tax_rate', field=models.DecimalField(decimal_places=2, default=0, max_digits=5)),
        migrations.AlterField(model_name='product', name='tax_rate', field=models.DecimalField(decimal_places=2, default=0, max_digits=5)),
        migrations.AlterField(model_name='booking', name='tax_rate_quoted', field=models.DecimalField(decimal_places=2, default=0, max_digits=5)),
        migrations.AlterField(model_name='estimateline', name='tax_rate', field=models.DecimalField(decimal_places=2, default=0, max_digits=5)),
    ]
