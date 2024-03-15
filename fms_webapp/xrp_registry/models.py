from django.db import models

class Device(models.Model):
    STATES = [
        ('unknown',    'UNKNOWN'),
        ('registered', 'REGISTERED'),
        ('unregistered', 'UNREGISTERED')
    ]

    PROTOCOLS = [
        ('tcp', 'TCP'),
        ('udp', 'UDP')
    ]

    hardware_id = models.CharField(max_length = 32, blank=False, default='Unassigned')
    type        = models.CharField(max_length = 32, blank=False, default='Unknown')
    name        = models.CharField(max_length = 32, blank=False, default='Unassigned')
    ip_address  = models.CharField(max_length = 32, blank=False, default='Unassigned')
    port        = models.CharField(max_length = 8, blank=False, default='9999')
    protocol    = models.CharField(max_length = 16, choices=PROTOCOLS, blank=False, default='TCP')
    state       = models.CharField(max_length = 32, choices=STATES, blank=False, default='UNKNOWN')
    status      = models.CharField(max_length = 32, blank=True, default='')

    def __str__(self):
        return self.hardware_id

