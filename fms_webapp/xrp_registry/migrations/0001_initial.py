# Generated by Django 5.0.2 on 2024-02-27 18:17

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hardware_id', models.CharField(default='Unassigned', max_length=32)),
                ('ip_address', models.CharField(default='Unassigned', max_length=32)),
                ('port', models.CharField(default='9999', max_length=8)),
                ('protocol', models.CharField(choices=[('tcp', 'TCP'), ('udp', 'UDP')], default='TCP', max_length=16)),
                ('state', models.CharField(choices=[('unknown', 'UNKNOWN'), ('registered', 'REGISTERED')], default='UNKNOWN', max_length=32)),
            ],
        ),
    ]