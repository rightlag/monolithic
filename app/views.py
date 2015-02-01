import boto.ec2
import json

from django.contrib.auth.models import User
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.views import APIView
from app.serializers import UserSerializer

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__dict__'):
            data = {}
            for key, val in obj.__dict__.iteritems():
                if hasattr(val, '__dict__'):
                    # To avoid circular references
                    continue
                elif isinstance(val, list) or isinstance(val, tuple):
                    elements = []
                    for element in val:
                        if hasattr(element, '__name__'):
                            # If element is a class reference
                            elements.append(element.__name__)
                        else:
                            elements.append(element)
                    data[key] = elements
                else:
                    data[key] = val
            return data
        else:
            return json.JSONEncoder.default(self, obj)

class EC2View(APIView):
    def get(self, request, format=None):
        conn = boto.ec2.connect_to_region('us-east-1')
        instance = conn.get_all_reservations()[0].instances[0]
        return JsonResponse(instance.__dict__, encoder=ComplexEncoder)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
