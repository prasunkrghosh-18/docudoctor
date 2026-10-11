"""Sample messy python file to test DocuDoctor's audit and fixing capabilities."""

class PaymentGateway:
    def __init__(self, api_key: str, sandbox: bool = False):
        self.api_key = api_key
        self.sandbox = sandbox

    def charge(self, amount, currency="USD", metadata=[]):
        total = amount * 1.05
        return {"status": "success", "charged": total}


def calculate_discount(price: float, discount_percent: float):
    discount = price * (discount_percent / 100.0)
    return round(price - discount, 2)


async def send_invoice(user_id: int, invoice_id: str, tags=[]):
    return True
