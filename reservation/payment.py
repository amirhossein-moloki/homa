from django.conf import settings
from django.urls import reverse
from zarinpal import ZarinPal
from .config import Config
from .models import Reservation
from rest_framework import serializers


class ZarinpalGateway:
    """
    A class to encapsulate all interactions with the Zarinpal payment gateway.
    """
    def __init__(self, request=None):
        merchant_id = getattr(settings, 'ZARINPAL_MERCHANT_ID', 'YOUR_MERCHANT_ID')
        # In a real application, sandbox mode should also be configured via settings.
        config = Config(merchant_id=merchant_id, sandbox=True)
        self.zarinpal = ZarinPal(config)
        self.request = request

    def _get_sanitized_amount(self, total_price):
        """
        Ensures the amount meets Zarinpal's minimum requirement.
        """
        amount = int(total_price)
        # Zarinpal has a minimum amount, which is 1000 Toman (10,000 Rials).
        return max(amount, 10000)

    def create_payment_request(self, reservation: Reservation):
        """
        Initiates a payment request with Zarinpal.

        Args:
            reservation: The Reservation object for which to create the payment.

        Returns:
            A tuple containing the payment URL and the authority code.

        Raises:
            ValueError: If the request object was not provided during initialization.
            Exception: If Zarinpal fails to return a valid authority.
        """
        if not self.request:
            raise ValueError("A request object is required to build the absolute callback URL.")

        amount = self._get_sanitized_amount(reservation.total_price)
        callback_url = self.request.build_absolute_uri(reverse('payment-callback'))

        payment_data = {
            "amount": amount,
            "callback_url": callback_url,
            "description": f"Reservation for {reservation.hall.name} - ID: {reservation.id}",
            "email": getattr(reservation.user, 'email', ''),
            "mobile": getattr(reservation.user, 'phone_number', ''),
        }

        res = self.zarinpal.payments.create(payment_data)

        if res.get("data") and res.get("data", {}).get("authority"):
            authority = res["data"]["authority"]
            payment_url = self.zarinpal.payments.generate_payment_url(authority)
            return payment_url, authority
        else:
            error_details = res.get("errors", "Unknown error from payment gateway.")
            raise serializers.ValidationError(
                {"error": "Could not get payment authority from gateway.", "details": error_details}
            )

    def verify_payment(self, reservation: Reservation, authority: str):
        """
        Verifies a payment with Zarinpal using the authority from the callback.

        Args:
            reservation: The reservation object tied to the payment.
            authority: The authority code from the Zarinpal callback.

        Returns:
            A tuple containing a boolean success status and the result details
            (either a reference ID on success or error details on failure).
        """
        amount = self._get_sanitized_amount(reservation.total_price)

        verification_data = {
            "amount": amount,
            "authority": authority,
        }

        res = self.zarinpal.verifications.verify(verification_data)

        # Code 100 means success.
        # Code 101 means the payment was already successfully verified.
        if res.get("data") and res["data"].get("code") in [100, 101]:
            ref_id = res["data"].get("ref_id")
            # If the payment was already verified, the status of our reservation should reflect that.
            if res["data"].get("code") == 101 and reservation.status == Reservation.ReservationStatus.PENDING:
                 reservation.status = Reservation.ReservationStatus.ACTIVE
                 reservation.save()
            return True, ref_id
        else:
            error_details = res.get("errors") or res.get("data")
            return False, error_details
