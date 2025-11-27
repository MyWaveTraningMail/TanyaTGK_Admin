import uuid
from yookassa import Configuration, Payment
from config import YOO_KASSA_SHOP_ID, YOO_KASSA_SECRET_KEY, BOT_USERNAME

Configuration.account_id = YOO_KASSA_SHOP_ID
Configuration.secret_key = YOO_KASSA_SECRET_KEY


async def create_payment_link(amount: int, description: str, user_id: int, booking_id: int):
    payment = Payment.create({
        "amount": {
            "value": f"{amount}.00",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"https://t.me/{BOT_USERNAME.lstrip('@')}?start=paid_{booking_id}"
        },
        "capture": True,
        "description": description,
        "metadata": {
            "user_id": str(user_id),
            "booking_id": str(booking_id)
        }
    })

    return payment.confirmation.confirmation_url, payment.id
