
from rest_framework import serializers

from .models import Device

class DeviceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Device
        fields = ('hardware_id', 'type', 'name', 'ip_address', 'port', 'protocol', 'state', 'status')

