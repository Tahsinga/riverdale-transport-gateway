from django.db import migrations, models
import decimal


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0004_ridelog_bus_id_ridelog_timestamp'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemconfig',
            name='min_balance',
            field=models.DecimalField(default=decimal.Decimal('0.00'), max_digits=10, decimal_places=2),
        ),
    ]
