"""Razorpay (test mode) behind a few small functions. While MOCK_EXTERNALS=true nothing leaves this computer.

Secrets come only from settings (environment variables) and are never logged.
"""
import hashlib
import hmac
import secrets

from django.conf import settings

MOCK_SECRET = "mock-razorpay-secret"  # only used for the fake checkout


def is_mock() -> bool:
    return settings.MOCK_EXTERNALS or not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def _secret() -> str:
    return MOCK_SECRET if is_mock() else settings.RAZORPAY_KEY_SECRET


def sign(order_id: str, payment_id: str) -> str:
    """Razorpay's signature: HMAC-SHA256 of "order_id|payment_id" with the key secret."""
    return hmac.new(_secret().encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


def verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    return hmac.compare_digest(sign(order_id, payment_id), signature or "")


def create_order(amount_paise: int, invoice_id: int) -> dict:
    """An order for `amount_paise` (receipt = the invoice id). The fake order also carries a ready-made
    payment id and signature so the demo checkout can finish without Razorpay."""
    if is_mock():
        order_id = f"order_mock_{invoice_id}_{amount_paise}_{secrets.token_hex(4)}"
        payment_id = f"pay_mock_{secrets.token_hex(6)}"
        return {"order_id": order_id, "amount": amount_paise, "currency": "INR", "key_id": "rzp_test_mock",
                "mock": True, "mock_payment_id": payment_id, "mock_signature": sign(order_id, payment_id)}
    import razorpay
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    order = client.order.create({"amount": amount_paise, "currency": "INR", "receipt": str(invoice_id)})
    return {"order_id": order["id"], "amount": order["amount"], "currency": order["currency"],
            "key_id": settings.RAZORPAY_KEY_ID, "mock": False}


def order_details(order_id: str) -> dict:
    """{amount, receipt} of an order we created, taken from Razorpay (never from the browser)."""
    if is_mock():
        parts = order_id.split("_")  # order_mock_<invoice>_<amount>_<random>
        if len(parts) != 5 or parts[:2] != ["order", "mock"]:
            raise ValueError("Not a mock order")
        return {"receipt": parts[2], "amount": int(parts[3])}
    import razorpay
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    order = client.order.fetch(order_id)
    return {"receipt": str(order.get("receipt", "")), "amount": int(order["amount"])}
