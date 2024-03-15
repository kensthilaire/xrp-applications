from django.shortcuts import render

from django.http import HttpResponse

from rest_framework import viewsets
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt

from .models import Device
from .serializers import DeviceSerializer
from .utils import add_or_update_device, delete_device

class DeviceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows devices to be viewed or edited.
    """
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


def home(request):
    return render(request, "xrp_registry/home.html", {})
