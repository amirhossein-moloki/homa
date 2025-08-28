from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser, OTP
from .utils import send_otp
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import UserSerializer


class RequestOTP(APIView):
    @swagger_auto_schema(
        operation_summary="ارسال کد تایید",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='شماره تلفن'),
            }
        )
    )
    def post(self, request):
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response({'error': 'وارد کردن شماره تلفن الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        if send_otp(phone_number):
            return Response({'message': 'کد تایید با موفقیت ارسال شد.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'خطا در ارسال کد تایید.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyOTP(APIView):
    @swagger_auto_schema(
        operation_summary="تایید کد ارسال شده",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='شماره تلفن'),
                'code': openapi.Schema(type=openapi.TYPE_STRING, description='کد تایید'),
            }
        )
    )
    def post(self, request):
        phone_number = request.data.get('phone_number')
        code = request.data.get('code')

        if not phone_number or not code:
            return Response({'error': 'شماره تلفن و کد تایید الزامی است.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Find the latest OTP for this phone number
            otp_record = OTP.objects.filter(phone_number=phone_number).latest('created_at')

            # Check if OTP is locked
            if otp_record.failed_attempts >= 3:
                return Response({'error': 'کد تایید شما به دلیل تلاش های ناموفق قفل شده است. لطفا کد جدیدی درخواست کنید.'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if OTP has expired (e.g., 5 minutes validity)
            if otp_record.created_at < timezone.now() - timedelta(minutes=5):
                return Response({'error': 'کد تایید منقضی شده است.'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if the code is correct
            if otp_record.code != code:
                otp_record.failed_attempts += 1
                otp_record.save()
                return Response({'error': 'کد تایید نامعتبر است.'}, status=status.HTTP_400_BAD_REQUEST)

            # OTP is valid, get or create the user
            user, created = CustomUser.objects.get_or_create(
                phone_number=phone_number,
            )
            if created:
                user.is_verified = True
                user.full_name = 'کاربر جدید'
                user.save()


            if not user.is_active:
                user.is_active = True
                user.save()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            # Mark the OTP as used by deleting it
            otp_record.delete()

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)

        except OTP.DoesNotExist:
            return Response({'error': 'کد تایید نامعتبر است.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': 'خطایی رخ داده است.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
