from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('detections', '0007_detection_latitude_detection_longitude'),
    ]

    operations = [
        migrations.AlterField(
            model_name='detection',
            name='status',
            field=models.CharField(
                choices=[
                    ('new', 'New'),
                    ('pending', 'Pending'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]
