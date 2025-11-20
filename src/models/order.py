from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Order:
    code: str
    status: str
    invoice_id: Optional[str]
    method: str
    order_date: datetime
    motorized: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert order to dictionary"""
        return {
            'code': self.code,
            'status': self.status,
            'invoice_id': self.invoice_id,
            'method': self.method,
            'order_date': self.order_date.isoformat(),
            'motorized': self.motorized
        }


@dataclass
class OrderAudit:
    order_code: str
    status: str
    timestamp: datetime
    motorized: Optional[str] = None

    def to_string(self) -> str:
        """Convert audit record to string"""
        motorized_info = f" - Motorizado: {self.motorized}" if self.motorized else ""
        return (
            f"Código: {self.order_code}\n"
            f"Estado: {self.status}\n"
            f"Fecha: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            f"{motorized_info}"
        )


@dataclass
class ReprintRequest:
    document_type: str
    document_id: str
    store_code: str
    reason: str
    timestamp: datetime
    user_id: int

    def get_reprint_key(self) -> str:
        """Get unique key for reprint tracking"""
        return f"{self.document_type}_{self.document_id}"