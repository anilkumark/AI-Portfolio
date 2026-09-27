"""Custom exceptions for the refund system."""


class RefundSystemError(Exception):
    """Base class for all application-specific errors."""


class CustomerNotFoundError(RefundSystemError):
    """Raised when a customer ID doesn't exist in the database."""

    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        super().__init__(f"Customer not found: {customer_id}")


class OrderNotFoundError(RefundSystemError):
    """Raised when an order ID doesn't exist in the database."""

    def __init__(self, order_id: str):
        self.order_id = order_id
        super().__init__(f"Order not found: {order_id}")


class ApprovalRequestError(RefundSystemError):
    """Raised when an approval decision link is invalid, expired, or already resolved."""
