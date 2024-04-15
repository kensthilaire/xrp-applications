from django.shortcuts import render

from django.http import HttpResponse

from rest_framework import viewsets
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt

from .models import Device
from .serializers import DeviceSerializer
from .utils import add_or_update_device, update_device_status, delete_device


class DeviceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows devices to be viewed or edited.
    """
    def get_queryset(self):
        queryset = Device.objects.all()
        id = self.request.query_params.get('id', None)
        if id is not None:
            queryset = queryset.filter(hardware_id=id)
        device_type = self.request.query_params.get('type', None)
        if device_type is not None:
            queryset = queryset.filter(type=device_type)
        alliance = self.request.query_params.get('alliance', None)
        if alliance is not None:
            if alliance.lower() != 'any':
                queryset = queryset.filter(alliance=alliance)

        return queryset

    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

@csrf_exempt
@api_view(http_method_names=['POST','DELETE'])
def register(request):
    if request.method == 'POST':
        ret_val = add_or_update_device( request.data )
        return HttpResponse(ret_val)
    elif request.method == 'DELETE':
        ret_val = delete_device(request.data)
        return HttpResponse(ret_val)
    return HttpResponse("Failed")

@csrf_exempt
@api_view(http_method_names=['POST'])
def status(request):
    if request.method == 'POST':
        ret_val = update_device_status( request.data )
        return HttpResponse(ret_val)
    return HttpResponse("Failed")

@csrf_exempt
@api_view(http_method_names=['POST'])
def update(request):
    if request.method == 'POST':
        ret_val = add_or_update_device( request.data )
        return HttpResponse(ret_val)
    return HttpResponse("Failed")

def home(request):
    return render(request, "xrp_registry/home.html", {})
