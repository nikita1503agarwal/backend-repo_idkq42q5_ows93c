"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    price_cents: int = Field(..., ge=0, description="Price in cents")
    image: Optional[str] = Field(None, description="Product image URL")
    cacao_percent: Optional[int] = Field(None, ge=0, le=100, description="Cacao percentage")
    in_stock: bool = Field(True, description="Whether product is in stock")
    stock_qty: Optional[int] = Field(20, ge=0, description="Inventory quantity")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for filtering")

class OrderItem(BaseModel):
    product_id: str = Field(..., description="Product document _id as string")
    quantity: int = Field(..., ge=1)
    unit_price_cents: Optional[int] = Field(None, ge=0)
    subtotal_cents: Optional[int] = Field(None, ge=0)

class CustomerInfo(BaseModel):
    name: str
    email: str
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = "US"

class Order(BaseModel):
    """
    Orders collection schema
    Collection name: "order"
    """
    items: List[OrderItem]
    currency: str = Field("usd", description="ISO currency code")
    total_cents: int = Field(..., ge=0)
    status: str = Field("pending", description="pending|paid|failed|canceled")
    payment_intent_id: Optional[str] = None
    client_secret: Optional[str] = None
    customer: Optional[CustomerInfo] = None
