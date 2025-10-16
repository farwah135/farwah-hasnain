from enum import Enum
from typing import List, Optional, Tuple
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(title="Restaurant Order Management", version="1.0.0")

# =====================
# 1) Data Models
# =====================

class OrderStatus(str, Enum):
    pending = "pending"       # Order has been placed but not started
    preparing = "preparing"   # Kitchen is preparing the order
    ready = "ready"           # Order is ready for pickup/serving
    delivered = "delivered"   # Order has been delivered to the customer

class OrderItem(BaseModel):
    dish_name: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0, description="Number of units ordered (must be > 0)")
    price: float = Field(..., gt=0, description="Unit price (must be > 0)")

class Order(BaseModel):
    id: Optional[int] = None
    customer_name: str
    table_number: int = Field(..., ge=1)
    items: List[OrderItem]
    status: OrderStatus = OrderStatus.pending
    total_amount: Optional[float] = None

# Input model for creating an order (no id/total/status in request)
class OrderCreate(BaseModel):
    customer_name: str
    table_number: int = Field(..., ge=1)
    items: List[OrderItem]

# Input model for status update
class StatusUpdate(BaseModel):
    status: OrderStatus

# =====================
# 2) In-memory storage
# =====================

orders: List[Order] = []
order_counter = 1  # For auto-generating IDs


# =====================
# Helper functions
# =====================

def calculate_total(items: List[OrderItem]) -> float:
    return round(sum(i.quantity * i.price for i in items), 2)

def find_order_by_id(order_id: int) -> Tuple[int, Order]:
    for idx, order in enumerate(orders):
        if order.id == order_id:
            return idx, order
    raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

def filter_orders(
    status: Optional[OrderStatus],
    table_number: Optional[int],
    customer_name: Optional[str]
) -> List[Order]:
    results = orders
    if status is not None:
        results = [o for o in results if o.status == status]
    if table_number is not None:
        results = [o for o in results if o.table_number == table_number]
    if customer_name is not None:
        needle = customer_name.strip().lower()
        results = [o for o in results if needle in o.customer_name.lower()]
    return results


# =====================
# Endpoints
# =====================

@app.post("/orders/", response_model=Order, status_code=201)
def create_order(payload: OrderCreate):
    global order_counter
    new_order = Order(
        id=order_counter,
        customer_name=payload.customer_name,
        table_number=payload.table_number,
        items=payload.items,
        status=OrderStatus.pending,
        total_amount=calculate_total(payload.items),
    )
    orders.append(new_order)
    order_counter += 1
    return new_order

@app.get("/orders/", response_model=List[Order])
def get_orders(
    status: Optional[OrderStatus] = Query(None, description="Filter by status"),
    table_number: Optional[int] = Query(None, ge=1, description="Filter by table number"),
    customer_name: Optional[str] = Query(None, description="Filter by customer name (case-insensitive, substring match)")
):
    return filter_orders(status, table_number, customer_name)

@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: int):
    _, order = find_order_by_id(order_id)
    return order

@app.patch("/orders/{order_id}/status", response_model=Order)
def update_status(order_id: int, update: StatusUpdate):
    idx, order = find_order_by_id(order_id)
    updated = order.copy(update={"status": update.status})
    orders[idx] = updated
    return updated

@app.delete("/orders/{order_id}")
def delete_order(order_id: int):
    idx, _ = find_order_by_id(order_id)
    orders.pop(idx)
    return {"detail": f"Order {order_id} deleted successfully"}