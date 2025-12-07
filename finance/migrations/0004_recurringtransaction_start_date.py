# Generated manually

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0003_transaction_recurring_transaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='recurringtransaction',
            name='start_date',
            field=models.DateField(default=django.utils.timezone.now, help_text='Data inicial do lançamento recorrente'),
        ),
    ]

