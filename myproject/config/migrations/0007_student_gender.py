from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0006_unregisteredtag'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='gender',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]