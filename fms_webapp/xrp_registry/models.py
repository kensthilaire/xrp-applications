from django.db import models

class Device(models.Model):
    STATES = [
        ('unknown',    'UNKNOWN'),
        ('registered', 'REGISTERED'),
        ('unregistered', 'UNREGISTERED'),
        ('running', 'RUNNING')
    ]

    PROTOCOLS = [
        ('tcp', 'TCP'),
        ('udp', 'UDP')
    ]

    ALLIANCES = [
        ('any', 'ANY'),
        ('red', 'RED'),
        ('blue', 'BLUE')
    ]

    hardware_id    = models.CharField(max_length = 36, blank=False, default='Unassigned')
    state          = models.CharField(max_length = 32, choices=STATES, blank=False, default='UNKNOWN')
    type           = models.CharField(max_length = 32, blank=False, default='Unknown')
    ip_address     = models.CharField(max_length = 32, blank=False, default='Unassigned')
    port           = models.CharField(max_length = 8, blank=False, default='9999')
    protocol       = models.CharField(max_length = 16, choices=PROTOCOLS, blank=False, default='TCP')
    name           = models.CharField(max_length = 32, blank=True, default='Unassigned')
    application    = models.CharField(max_length = 64, blank=True, default='Unknown')
    version        = models.CharField(max_length = 32, blank=True, default='Unknown')
    status         = models.CharField(max_length = 32, blank=True, default='Unknown')
    last_reported  = models.CharField(max_length = 64, blank=True, default='Never')
    last_timestamp = models.PositiveIntegerField(blank=True, default=0)
    alliance       = models.CharField(max_length = 32, choices=ALLIANCES, blank=True, default='ANY')

    def __str__(self):
        return self.hardware_id

