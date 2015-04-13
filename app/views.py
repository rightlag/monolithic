import boto
import boto.ec2
import boto.ec2.cloudwatch
import boto.exception
import boto.s3
import boto.ses.exceptions
import datetime
import json

from app import email
from app import models
from app import serializers
from django.contrib.auth.models import User
from django.core import exceptions
from django.core.mail import send_mail
from django.http import JsonResponse
from django.utils.crypto import get_random_string
from rest_framework import decorators
from rest_framework import permissions
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
    def post(self, request, format=None):
        """Get all reservations based on region."""
        region = request.data['region']
        conn = boto.ec2.connect_to_region(region)
        reservations = conn.get_all_reservations()
        return JsonResponse(reservations, encoder=ComplexEncoder, safe=False)

class ReservationDetail(APIView):
    def post(self, request, reservation_id, format=None):
        """Get a reservation based on region and instance id."""
        region = request.data['region']
        conn = boto.ec2.connect_to_region(region)
        filters = {
            'reservation-id': reservation_id,
        }
        try:
            reservation = conn.get_all_reservations(filters=filters)[0]
        except IndexError, e:
            # The specified reservation does not exist, return a 400 bad
            # request.
            return Response(e.message, status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse(reservation.__dict__, encoder=ComplexEncoder)

class InstanceDetail(APIView):
    def get(self, request, instance_id, format=None):
        """Get an instance based on region and instance id."""
        region = request.data['region']
        conn = boto.ec2.connect_to_region(region)
        instance_ids = [instance_id,]
        try:
            instance = conn.get_only_instances(instance_ids=instance_ids)[0]
        except IndexError, e:
            # The specified instance does not exist, return a 400 bad
            # request.
            return Response(e.message, status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse(instance.__dict__, encoder=ComplexEncoder)

@decorators.api_view(['GET'])
def spot_price_history(request, instance_id, format=None):
    """Calculate the estimated monthly cost for a specific EC2
    instance."""
    region = request.data['region']
    conn = boto.ec2.connect_to_region(region)
    instance_ids = [instance_id,]
    try:
        instance = conn.get_only_instances(instance_ids=instance_ids)[0]
    except IndexError, e:
        return Response(e.message, status=status.HTTP_400_BAD_REQUEST)
    # Based on the current instance, build a dictionary to pass as an
    # argument to the `get_spot_price_history` method.
    params = {
        'availability_zone': instance._placement,
        'instance_type': instance.instance_type,
        'product_description': ('Linux/UNIX (Amazon VPC)'
                                if not instance.platform
                                else instance.platform),
    }
    spot_price_history = conn.get_spot_price_history(**params)
    monthly_total = sum([instance.price for instance in spot_price_history])
    return Response(monthly_total, status=status.HTTP_200_OK)

@decorators.api_view(['GET'])
def metrics(request, instance_id, format=None):
    """Get metric data for a specific EC2 instance."""
    # Need to configure default values for metric data within core
    # module and handle both GET and POST request methods.
    region = request.data['region']
    conn = boto.ec2.cloudwatch.connect_to_region(region)
    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(hours=12)
    dimensions = {'InstanceId': instance_id,}
    statistics = conn.get_metric_statistics(1800,
                                            start_time,
                                            end_time,
                                            'CPUUtilization',
                                            'AWS/EC2',
                                            ['Average',],
                                            dimensions=dimensions)
    return Response(statistics, status=status.HTTP_200_OK)

class BucketList(APIView):
    def post(self, request, format=None):
        """Get all buckets based on region."""
        region = request.data['region']
        conn = boto.s3.connect_to_region(region)
        buckets = conn.get_all_buckets()
        return JsonResponse(buckets, encoder=ComplexEncoder, safe=False)

@decorators.api_view(['GET'])
def S3Summary(request):
    """Retrieve total amount of buckets and the total size for all
    buckets."""
    region = request.data['region']
    conn = boto.s3.connect_to_region(region)
    buckets = conn.get_all_buckets()
    size = 0
    for bucket in buckets:
        for key in bucket.get_all_keys():
            # Increment key size (in bytes).
            size += key.size
    return Response({
        'buckets': len(buckets),
        'size': size,
    }, status=status.HTTP_200_OK)

@decorators.api_view(['GET'])
def EC2Summary(request):
    region = request.data['region']
    conn = boto.ec2.connect_to_region(rergion)
    response = {}
    response['running'] = conn.get_only_instances(
        filters={
            'instance_state_name': 'running',
        }
    )
    response['running'] = len(response['running'])
    response['volumes'] = conn.get_all_volumes()
    response['volumes'] = len(response['volumes'])
    response['active'] = conn.get_all_reservations(
        filters={
            'instance_state_name': 'running',
        }
    )
    response['active'] = len(response['active'])
    response['retired'] = conn.get_all_reservations(
        filters={
            'instance_state_name': 'stopped',
        }
    )
    response['retired'] = len(response['retired'])
    return Response(response, status=status.HTTP_200_OK)

class PolicyDetail(APIView):
    pass

class KeyList(APIView):
    def post(self, request, bucket, format=None):
        """Get all keys in a bucket based on region."""
        region = request.data['region']
        conn = boto.s3.connect_to_region(region)
        try:
            bucket = conn.get_bucket(bucket)
        except boto.exception.S3ResponseError, e:
            return Response(e.message, status=status.HTTP_400_BAD_REQUEST)
        keys = bucket.get_all_keys()
        return JsonResponse(keys, encoder=ComplexEncoder, safe=False)

class KeyDetail(APIView):
    def get(self, request, region, bucket, key, format=None):
        region = request.data['region']
        conn = boto.s3.connect_to_region(region)
        try:
            bucket = conn.get_bucket(bucket)
        except boto.exception.S3ResponseError, e:
            return Response(e.message, status=status.HTTP_404_NOT_FOUND)
        key = bucket.get_key(key)
        return JsonResponse(key.__dict__, encoder=ComplexEncoder)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer

    @decorators.list_route(methods=['POST'],
                           permission_classes=[permissions.AllowAny])
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

    @decorators.list_route(methods=['POST'],
                           permission_classes=[permissions.AllowAny])
    def reset(self, request, format=None):
        """Reset user password.

        This method can be called for authenicated or non-authenticated
        users.
        """
        if request.auth:
            if not request.user.check_password(request.data['current_pass']):
                return Response(('Password entered does not match current '
                                 'password'),
                                status=status.HTTP_400_BAD_REQUEST)
            request.user.set_password(request.data['new_pass'])
            request.user.save()
            return Response('Password has been reset successfully',
                            status=status.HTTP_200_OK)
        else:
            context = {'request': request,}
            serializer = serializers.PasswordSerializer(request.data,
                                                        context=context)
            try:
                user = User.objects.get(username=serializer.data['username'])
            except exceptions.ObjectDoesNotExist, e:
                return Response(e.message, status=status.HTTP_404_NOT_FOUND)
            password = get_random_string(length=8)
            user.set_password(password)
            user.save()
            try:
                send_mail(email.ACCOUNT_RESET_PASSWORD_SUBJECT,
                          email.ACCOUNT_RESET_PASSWORD_MESSAGE
                          .format(password),
                          email.FROM_EMAIL,
                          [user.email,],
                          fail_silently=False)
            except boto.ses.exceptions.SESError, e:
                return Response(e.message, status=status.HTTP_400_BAD_REQUEST)
            return Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.list_route(['GET', 'PUT'])
    def profile(self, request, format=None):
        """Update user profile. Two request methods are handled:

        GET:
          Used to fetch user object via `auth_token` sent in the HTTP
          request payload. Return a serialized instance of that user
          object.

        PUT:
          Used to update existing user object.
        """
        if request.method == 'GET':
            context = {'request': request,}
            serializer = serializers.ProfileSerializer(request.user,
                                                       context=context)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'PUT':
            serializer = serializers.ProfileSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.update(request.user, serializer.data)
                return Response(serializer.data, status=status.HTTP_200_OK)

class KeypairViewSet(viewsets.ModelViewSet):
    queryset = models.Keypair.objects.all()
    serializer_class = serializers.KeypairSerializer

    def create(self, request, format=None):
        import pdb
        pdb.set_trace()
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
        serializer = serializers.KeypairSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            keypair = serializer.create(serializer.data)
            request.user.keypair_set.add(keypair)
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)

@decorators.api_view(['GET'])
def access(request, format=None):
    """Determine if the user has AWS access key id(s) and secret
    key(s) associated with their account.

    Returns:
      HTTP_403_FORBIDDEN: If `user.keypair_set` returns an empty
        list object.
      HTTP_200_OK: If the `user.keypair_set` return a non-empty list
        object.
    """
    if not request.user.keypair_set.all():
        return Response(('User does not have access keys and secret keys '
                         'associated with account'),
                        status=status.HTTP_403_FORBIDDEN)
    return Response(status=status.HTTP_200_OK)

@decorators.api_view(['GET'])
@decorators.permission_classes([permissions.AllowAny])
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
