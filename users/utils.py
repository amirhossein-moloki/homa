import secrets
from django.conf import settings
from sms_ir import SmsIr
from .models import OTP
import logging

logger = logging.getLogger(__name__)

def send_otp(phone_number: str):
    """
    Generates a 6-digit OTP, saves it to the OTP model, and sends it via SMS.ir.
    """
    # Generate a cryptographically secure 6-digit code
    code = str(secrets.randbelow(900000) + 100000)

    # Save the OTP to the database
    OTP.objects.create(phone_number=phone_number, code=code)

    # Send the OTP using sms.ir
    try:
        sms_ir = SmsIr(
            settings.SMS_IR_API_KEY,
            settings.SMS_IR_LINE_NUMBER,
        )

        # The user's documentation shows `send_verify_code` needs parameters.
        # The library likely sends the generated code as one of the parameters.
        # I'll assume the template on sms.ir has a parameter named 'CODE'.
        parameters = [
            {
                "name": "CODE",
                "value": str(code),
            }
        ]

        sms_ir.send_verify_code(
            number=phone_number,
            template_id=int(settings.SMS_IR_OTP_TEMPLATE_ID),
            parameters=parameters,
        )

        logger.info(f"OTP sent to {phone_number}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP to {phone_number}: {e}")
        return False
