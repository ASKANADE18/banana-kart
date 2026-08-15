def send_order_confirmation_email(email: str, order_id: int) -> None:
    print(
        f"Sending order confirmation email to {email} "
        f"for order {order_id}"
    )