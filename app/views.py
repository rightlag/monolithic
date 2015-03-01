import boto.ec2
import boto.ec2.cloudwatch
import boto.ec2.connection
import boto.exception
import boto.s3
import boto.ses.exceptions
import datetime
import json
import sys

from app import email
from app import models
from app import serializers
from django.contrib.auth.models import User
from django.core import exceptions
from django.core.mail import send_mail
from django.http import JsonResponse
from rest_framework import decorators
from rest_framework import status
from rest_framework import viewsets
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

@decorators.api_view(['GET'])
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

@decorators.api_view(['GET'])
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

@decorators.api_view(['GET'])
def EC2Summary(request):
    conn = boto.ec2.connect_to_region('us-east-1')
    response = {}
    response['running'] = conn.get_only_instances(filters={
        'instance_state_name': 'running',
    })
    response['running'] = len(response['running'])
    response['volumes'] = conn.get_all_volumes()
    response['volumes'] = len(response['volumes'])
    response['active'] = None
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
    serializer_class = serializers.UserSerializer

    @decorators.list_route(methods=['POST'])
    def register(self, request, format=None):
        """Register a new user."""
        serializer = serializers.RegistrationSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            # Move this in the try/except block
            user = serializer.create(serializer.data)
            try:
                send_mail(email.ACCOUNT_ACTIVATION_SUBJECT,
                          email.ACCOUNT_ACTIVATION_MESSAGE
                          .format(user.verification),
                          email.FROM_EMAIL,
                          [serializer.data['email'],],
                          fail_silently=False)
            except boto.ses.exceptions.SESError, e:
                return Response(e.message, status=status.HTTP_400_BAD_REQUEST)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @decorators.list_route(methods=['POST'])
    def reset(self, request, format=None):
        """Reset user password."""
        serializer = serializers.PasswordSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                user = User.objects.get(email=serializer.data['email'])
            except exceptions.ObjectDoesNotExist, e:
                return Response(e.message, status=status.HTTP_404_NOT_FOUND)
            return Response(serializer.data, status=HTTP_200_OK)

    @decorators.detail_route(['GET', 'PUT'])
    def profile(self, request, pk=None, format=None):
        """Update user profile. Two request methods are handled:

        Raises:
          ObjectDoesNotExist: If user object is not found.

        GET:
          Used to fetch user object and return a serialized
          instance of that user object.

        PUT:
          Used to update existing user object.
        """
        try:
            user = User.objects.get(auth_token=pk)
        except exceptions.ObjectDoesNotExist, e:
            return Response(e.message, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'GET':
            context = {'request': request,}
            serializer = serializers.UserSerializer(user,
                                                    context=context)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = serializers.ProfileSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.update(user, serializer.data)
                return Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.detail_route(['GET'])
    def access(self, request, pk=None, format=None):
        """Determine if the user has AWS access key id(s) and secret
        key(s) associated with their account.

        Returns:
          HTTP_403_FORBIDDEN: If `user.keypair_set` returns an empty
            list object.
          HTTP_200_OK: If the `user.keypair_set` return a non-empty list
            object.
        """
        try:
            user = User.objects.get(auth_token=pk)
        except exceptions.ObjectDoesNotExist, e:
            return Response(e.message, status=status.HTTP_404_NOT_FOUND)
        if not user.keypair_set.all():
            return Response(('User does not have access keys and secret keys '
                             'associated with account'),
                            status=status.HTTP_403_FORBIDDEN)
        return Response(status=status.HTTP_200_OK)

    @decorators.detail_route(['POST', 'PUT'])
    def keypair(self, request, pk=None, format=None):
        """This method allows users to manipulate their AWS access and
        secret key pairs. There are two checks to this method:

        The first check determines whether or not the user exists by
        verifying the authorization token that is passed specified in
        the URL.

        The second check attempts to make a call to AWS EC2 endpoint to
        query all available EC2 regions. If the reuest returns a status
        code of 401 Unauthorized, then the access and secret keys will
        NOT be persisted to the database.
        """
        try:
            user = User.objects.get(auth_token=pk)
        except exceptions.ObjectDoesNotExist, e:
            return Response(e.message, status=status.HTTP_404_NOT_FOUND)
        access_key = request.data['access_key']
        secret_key = request.data['secret_key']
        conn = (boto
                .ec2
                .connection
                .EC2Connection(aws_access_key_id=access_key,
                               aws_secret_access_key=secret_key))
        try:
            conn.get_all_regions()
        except boto.exception.EC2ResponseError, e:
            return Response(e.message, status=status.HTTP_401_UNAUTHORIZED)
        if request.method == 'POST':
            serializer = serializers.KeypairSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                keypair = serializer.create(serializer.data)
                user.keypair_set.add(keypair)
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)

@decorators.api_view(['GET'])
def verify(request, verification_code=None, format=None):
    """Function used to verify user account. Token is passed to the URI
    and checked against the value stored in the database during the
    registration process."""
    code = verification_code
    try:
        verification = models.Verification.objects.get(verification_code=code)
    except exceptions.ObjectDoesNotExist, e:
        return Response(e.message, status=status.HTTP_404_NOT_FOUND)
    # Verification token matches. Update `is_active` flag to True.
    user = verification.user
    if user.is_active:
        # User is already active, return a HTTP 400 BAD REQUEST.
        return Response('User is already activated',
                        status=status.HTTP_400_BAD_REQUEST)
    user.is_active = True
    user.save()
    return Response('Account activation successful',
                    status=status.HTTP_200_OK)
