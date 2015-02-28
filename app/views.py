import boto.ec2
import boto.ec2.cloudwatch
import boto.exception
import boto.s3
import datetime
import json
import sys

from app.serializers import RegistrationSerializer, ProfileSerializer, UserSerializer, PasswordSerializer
from django.contrib.auth.models import User
from django.core import exceptions
from django.core import serializers
from django.http import JsonResponse
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import api_view, detail_route, list_route
from rest_framework.response import Response
from rest_framework.views import APIView

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

class ReservationList(APIView):
    def get(self, request, format=None):
        conn = boto.ec2.connect_to_region('us-east-1')
        reservations = conn.get_all_reservations()
        return JsonResponse(reservations, encoder=ComplexEncoder, safe=False)

class ReservationDetail(APIView):
    def get(self, request, reservation_id, format=None):
        conn = boto.ec2.connect_to_region('us-east-1')
        filters = {
            'reservation-id': reservation_id,
        }
        reservation = conn.get_all_reservations(filters=filters)
        return JsonResponse(reservation[0].__dict__, encoder=ComplexEncoder)

class InstanceDetail(APIView):
    def get(self, request, instance_id, format=None):
        """Get an instance based on region and instance id."""
        conn = boto.ec2.connect_to_region('us-east-1')
        instance_ids = [instance_id,]
        instance = conn.get_only_instances(instance_ids=instance_ids)
        return JsonResponse(instance[0].__dict__, encoder=ComplexEncoder)

@api_view(['GET'])
def metrics(request, instance_id, format=None):
    """Get metric data for a specific EC2 instance."""
    # need to configure default values for metric data within core module
    conn = boto.ec2.cloudwatch.connect_to_region('us-east-1')
    start_time = datetime.datetime(2015, 2, 9, 8, 0, 0, 0)
    end_time = datetime.datetime(2015, 2, 10, 14, 0, 0, 0)
    dimensions = {'InstanceId': instance_id}
    statistics = conn.get_metric_statistics(1800,
                                            start_time,
                                            end_time,
                                            'CPUUtilization',
                                            'AWS/EC2',
                                            ['Average'],
                                            dimensions=dimensions)
    return Response(statistics, status=status.HTTP_200_OK)

class BucketList(APIView):
    def get(self, request, format=None):
        """Get all buckets based on region."""
        conn = boto.s3.connect_to_region('us-east-1')
        buckets = conn.get_all_buckets()
        return JsonResponse(buckets, encoder=ComplexEncoder, safe=False)

@api_view(['GET'])
def S3Summary(request):
    """Retrieve total amount of buckets and the total size for all
    buckets."""
    conn = boto.s3.connect_to_region('us-east-1')
    buckets = conn.get_all_buckets()
    size = 0
    for bucket in buckets:
        for key in bucket.get_all_keys():
            size += key.size
    return Response({
        'buckets': len(buckets),
        'size': size,
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
def EC2Summary(request):
    conn = boto.ec2.connect_to_region('us-east-1')
    response = {}
    response['running'] = conn.get_only_instances(filters={
        'instance_state_name': 'running',
    })
    response['running'] = len(response['running'])
    response['volumes'] = conn.get_all_volumes()
    response['volumes'] = len(response['volumes'])
    response['active'] = pass
    return Response(response, status=status.HTTP_200_OK)

class PolicyDetail(APIView):
    pass

class KeyList(APIView):
    def get(self, request, bucket, format=None):
        conn = boto.s3.connect_to_region('us-east-1')
        try:
            bucket = conn.get_bucket(bucket)
        except boto.exception.S3ResponseError, e:
            return Response('Invalid bucket name')
        keys = bucket.get_all_keys()
        return JsonResponse(keys, encoder=ComplexEncoder, safe=False)

class KeyDetail(APIView):
    def get(self, request, bucket, key, format=None):
        conn = boto.s3.connect_to_region('us-east-1')
        try:
            bucket = conn.get_bucket(bucket)
        except boto.exception.S3ResponseError, e:
            return Response('Invalid bucket name')
        key = bucket.get_key(key)
        return JsonResponse(key.__dict__, encoder=ComplexEncoder)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @list_route(methods=['POST'])
    def register(self, request, format=None):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.create(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @list_route(methods=['POST'])
    def reset(self, request, format=None):
        """Reset user password."""
        serializer = PasswordSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                user = User.objects.get(email=serializer.data['email'])
            except exceptions.ObjectDoesNotExist, e:
                return Response(e.message, status=status.HTTP_404_NOT_FOUND)
            return Response(serializer.data, status=HTTP_200_OK)

    @detail_route(['GET', 'POST'])
    def profile(self, request, pk=None, format=None):
        """Update profile route."""
        try:
            user = User.objects.get(auth_token=pk)
        except exceptions.ObjectDoesNotExist, e:
            return Response(e.message, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'GET':
            serializer = UserSerializer(user, context={'request': request})
            return Response(serializer.data)
        elif request.method == 'POST':
            serializer = ProfileSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.update(user, serializer.data)
                return Response(serializer.data, status=status.HTTP_200_OK)
