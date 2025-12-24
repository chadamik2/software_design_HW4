from decimal import Decimal

from pydantic import BaseModel, Field


class CreateAccountResponse(BaseModel):
    user_id: str
    balance: str


class TopUpRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)


class TopUpResponse(BaseModel):
    user_id: str
    balance: str


class BalanceResponse(BaseModel):
    user_id: str
    balance: str
