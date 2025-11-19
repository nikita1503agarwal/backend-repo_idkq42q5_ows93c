import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order, OrderItem, CustomerInfo

app = FastAPI(title="Luxury Chocolates API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductCreate(Product):
    pass

class ProductOut(Product):
    id: str

class SeedRequest(BaseModel):
    force: bool = False


@app.get("/")
def read_root():
    return {"message": "Luxury Chocolate Store Backend"}


@app.get("/api/products", response_model=List[ProductOut])
def list_products():
    try:
        items = db["product"].find({}).limit(100)
        results = []
        for doc in items:
            doc["id"] = str(doc["_id"])  # expose id
            doc.pop("_id", None)
            results.append(ProductOut(**doc))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/products", response_model=ProductOut)
def create_product(product: ProductCreate):
    try:
        pid = create_document("product", product)
        doc = db["product"].find_one({"_id": ObjectId(pid)})
        if not doc:
            raise HTTPException(status_code=404, detail="Product not found after creation")
        doc_out = {**{k: v for k, v in doc.items() if k != "_id"}, "id": str(doc["_id"]) }
        return ProductOut(**doc_out)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/seed")
def seed_products(payload: SeedRequest):
    # add a few luxury chocolate products if none exist, or force reseed
    try:
        count = db["product"].count_documents({})
        if count > 0 and not payload.force:
            return {"seeded": False, "count": count}
        if payload.force:
            db["product"].delete_many({})
        data = [
            {
                "name": "Grand Cru Truffle Box",
                "description": "Assortment of hand-rolled ganache truffles dusted with 24k gold.",
                "price_cents": 8900,
                "image": "https://images.unsplash.com/photo-1541976076758-347942db1970?q=80&w=1200&auto=format&fit=crop",
                "cacao_percent": 72,
                "in_stock": True,
                "stock_qty": 50,
                "tags": ["truffles", "gold", "gift"]
            },
            {
                "name": "Single-Origin Noir Bar",
                "description": "Peruvian single-origin 85% cacao with notes of cherry and espresso.",
                "price_cents": 1500,
                "image": "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?q=80&w=1200&auto=format&fit=crop",
                "cacao_percent": 85,
                "in_stock": True,
                "stock_qty": 200,
                "tags": ["bar", "single-origin", "vegan"]
            },
            {
                "name": "Praline Jewels",
                "description": "Hazelnut praline bonbons finished with shimmering cocoa butter.",
                "price_cents": 4200,
                "image": "https://images.unsplash.com/photo-1606313564200-e75d5e30476e?q=80&w=1200&auto=format&fit=crop",
                "cacao_percent": 64,
                "in_stock": True,
                "stock_qty": 120,
                "tags": ["bonbons", "praline", "assortment"]
            }
        ]
        for p in data:
            db["product"].insert_one(p)
        return {"seeded": True, "count": db["product"].count_documents({})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Payment flow using a mock provider (to avoid secrets). In a real app you'd integrate Stripe.
class CheckoutItem(BaseModel):
    product_id: str
    quantity: int

class CheckoutRequest(BaseModel):
    items: List[CheckoutItem]
    customer: Optional[CustomerInfo] = None

class CheckoutResponse(BaseModel):
    order_id: str
    client_secret: str
    amount_cents: int
    currency: str = "usd"
    status: str


def compute_totals(items: List[CheckoutItem]):
    total = 0
    prepared: List[OrderItem] = []
    for it in items:
        doc = db["product"].find_one({"_id": ObjectId(it.product_id)})
        if not doc or not doc.get("in_stock", False):
            raise HTTPException(status_code=400, detail=f"Product unavailable: {it.product_id}")
        price_cents = int(doc.get("price_cents", 0))
        subtotal = price_cents * it.quantity
        total += subtotal
        prepared.append(OrderItem(product_id=str(doc["_id"]), quantity=it.quantity, unit_price_cents=price_cents, subtotal_cents=subtotal))
    return total, prepared


@app.post("/api/checkout", response_model=CheckoutResponse)
def checkout(req: CheckoutRequest):
    # Create order in DB with status pending and return a mock client secret
    try:
        total, prepared_items = compute_totals(req.items)
        mock_client_secret = f"mock_secret_{ObjectId()}"
        order = Order(
            items=prepared_items,
            currency="usd",
            total_cents=total,
            status="pending",
            client_secret=mock_client_secret,
            customer=req.customer,
        )
        order_id = create_document("order", order)
        return CheckoutResponse(order_id=order_id, client_secret=mock_client_secret, amount_cents=total, currency="usd", status="pending")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PaymentConfirmRequest(BaseModel):
    order_id: str
    client_secret: str
    success: bool = True

class PaymentConfirmResponse(BaseModel):
    order_id: str
    status: str


@app.post("/api/confirm-payment", response_model=PaymentConfirmResponse)
def confirm_payment(req: PaymentConfirmRequest):
    # validate client_secret and update order status
    try:
        doc = db["order"].find_one({"_id": ObjectId(req.order_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Order not found")
        if doc.get("client_secret") != req.client_secret:
            raise HTTPException(status_code=400, detail="Invalid client secret")
        new_status = "paid" if req.success else "failed"
        db["order"].update_one({"_id": ObjectId(req.order_id)}, {"$set": {"status": new_status}})
        return PaymentConfirmResponse(order_id=req.order_id, status=new_status)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
