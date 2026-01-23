# Generated migration for adding color field to SubEvent model

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('pretixbase', '0296_invoice_invoice_from_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='subevent',
            name='color',
            field=models.CharField(
                blank=True,
                help_text='Hex color code for displaying this date in the calendar (e.g., #FF5733)',
                max_length=7,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message='Please enter a valid hex color code (e.g., #FF5733)',
                        regex='^#[0-9A-Fa-f]{6}$'
                    )
                ],
                verbose_name='Calendar color'
            ),
        ),
    ]
