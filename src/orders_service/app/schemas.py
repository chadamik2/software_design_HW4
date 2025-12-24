from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from .models import OrderStatus


class CreateOrderRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    description: str = Field("", max_length=512)


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    amount: str
    description: str
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
