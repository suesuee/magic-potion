import sqlalchemy
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
from src import database as db
from sqlalchemy import text


router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    limit = 5
    #page = int(search_page) if search_page else 1
    if search_page.startswith("?search_page="):
        try:
            page = int(search_page.split("=")[-1])
        except ValueError:
            page = 1
    else:
        page = 1
    offset = (page - 1) * limit

    if sort_col is search_sort_options.customer_name:
        order_by = db.customers.c.customer_name
    elif sort_col is search_sort_options.item_sku:
        order_by = db.potions_inventory.c.potion_name
    elif sort_col is search_sort_options.line_item_total:
        order_by = db.cart_items.c.gold_paid
    elif sort_col is search_sort_options.timestamp:
        order_by = db.cart_items.c.added_at
    else: 
        assert False, "Invalid sort option"
    
    # Do descending order if specified
    if sort_order == search_sort_order.desc:
        order_by = sqlalchemy.desc(order_by)
    
    stmt = (
        sqlalchemy.select(
            db.cart_items.c.id.label("line_item_id"),
            db.customers.c.customer_name,
            db.cart_items.c.qty.label("quantity"),
            db.potions_inventory.c.sku,
            db.potions_inventory.c.potion_name,
            db.cart_items.c.gold_paid.label("line_item_total"),
            db.cart_items.c.added_at.label("timestamp")
        )
        .select_from(
            db.cart_items
            .join(db.carts, db.cart_items.c.cart_id == db.carts.c.id)
            .join(db.customers, db.carts.c.customer_id == db.customers.c.id)
            .join(db.potions_inventory, db.cart_items.c.potion_id == db.potions_inventory.c.potion_id)
        )
        .order_by(order_by, db.carts.c.id)
        .limit(limit + 1)
        .offset(offset)
    )

    # Apply filters only if parameters are provided
    if customer_name:
        stmt = stmt.where(db.customers.c.customer_name.ilike(f"%{customer_name}%"))
    if potion_sku:
        stmt = stmt.where(db.potions_inventory.c.potion_name.ilike(f"%{potion_sku}%"))

    with db.engine.connect() as conn:
        result = conn.execute(stmt)
        rows = result.fetchall()

    has_next_page = len(rows) > limit
    json_result = []
    for row in rows[:limit]:
        item_sku_display = f"{row.quantity} {row.potion_name}s"
        timestamp_display = row.timestamp.isoformat()
        json_result.append(
            {
                "line_item_id": row.line_item_id,
                "item_sku": item_sku_display,
                "customer_name": row.customer_name,
                "line_item_total": row.line_item_total,
                "timestamp": timestamp_display
            }
        )
    # Pagination tokens for previous and next pages
    previous = f"?search_page={page-1}" if page > 1 else ""
    next = f"?search_page={page+1}" if has_next_page else ""

    return {
        "previous": previous,
        "next": next,
        "results": json_result
    }

    # return {
    #     "previous": "",
    #     "next": "",
    #     "results": [
    #         {
    #             "line_item_id": 1,
    #             "item_sku": "1 oblivion potion",
    #             "customer_name": "Scaramouche",
    #             "line_item_total": 50,
    #             "timestamp": "2021-01-01T00:00:00Z",
    #         }
    #     ],
    # }

class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    print(customers)

    # Update or insert customers in the database
    with db.engine.begin() as connection:
        customer_sql = """
        INSERT INTO customers (customer_name, customer_class, level)
        VALUES (:customer_name, :customer_class, :level)
        ON CONFLICT (customer_name) DO UPDATE
        SET customer_class = :customer_class, level = :level
        RETURNING id
        """
        customer_ids = []
        for customer in customers:
            # Insert or update each customer in the list
            result = connection.execute(sqlalchemy.text(customer_sql), {
                "customer_name": customer.customer_name,
                "customer_class": customer.character_class,
                "level": customer.level
            })
            customer_id = result.scalar()
            customer_ids.append(customer_id)

    # Return the list of customer IDs as confirmation
    return {
        "success": True,
        "customer_ids": customer_ids
    }


@router.post("/")
def create_cart(new_cart: Customer):
    """ Create a cart to store the quantity"""

    # Assume the customer already exists (updated in post_visits)
    with db.engine.begin() as connection:
        # Retrieve the customer ID from the database
        get_customer_sql = """
        SELECT id FROM customers WHERE customer_name = :customer_name
        """
        customer_result = connection.execute(sqlalchemy.text(get_customer_sql), {
            "customer_name": new_cart.customer_name
        })
        customer_id = customer_result.scalar()

        if not customer_id:
            raise ValueError("Customer does not exist. Please add the customer through post_visits first.")
        # Now, create a new cart for this customer
        create_cart_sql = """
        INSERT INTO carts (customer_id, created_at)
        VALUES (:customer_id, now())
        RETURNING id
        """
        cart_result = connection.execute(sqlalchemy.text(create_cart_sql), {
            "customer_id": customer_id
        })
        cart_id = cart_result.scalar()
        print(f"Cart_id in create cart: {cart_id}")
        print(f"Customer who created the cart: {new_cart.customer_name}")

    return {
        "cart_id": cart_id,
        "customer_name": new_cart.customer_name, 
        "character_class": new_cart.character_class,
        "level": new_cart.level
        }


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ Customers can add multiple items of green potions. Check cart and inventory first.  """

    # Update or insert the cart_items record
    with db.engine.begin() as connection:
        # Define the SQL statement to insert or update cart items
        create_cart_items_sql = """
            INSERT INTO cart_items (cart_id, potion_id, qty, added_at, gold_paid)
            SELECT :cart_id, potion_id, :qty, now(), :qty * price
            FROM potions_inventory
            WHERE potions_inventory.sku = :item_sku
            ON CONFLICT (cart_id, potion_id) DO UPDATE SET qty = :qty
            RETURNING id
        """

        # Execute the SQL statement with parameters
        cart_items_result = connection.execute(
            sqlalchemy.text(create_cart_items_sql), 
            {
                "cart_id": cart_id,
                "qty": cart_item.quantity,
                "item_sku": item_sku
            }
        )

        # Retrieve the cart item ID from the result
        cart_item_id = cart_items_result.scalar()
        print(f"Cart item ID in create cart: {cart_item_id}")

    print(f"cart id in set item quantity: {cart_id}, cart item id: {cart_item_id}")
    print(f"CI quantity: {cart_item.quantity} and item sku: {item_sku}")
    #print(f"customer who added potions to the cart: {customer_name}")
    
    return {
        "success": True,
        "message": "Potion added to cart",
        "quantity": cart_item.quantity
    }

class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ Make sure if potions are in the inventory before checking out """
    total_potions_bought = 0
    total_price = 0

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO potion_ledger(potion_id, potion_change)
            SELECT cart_items.potion_id, (cart_items.qty * -1)
            FROM cart_items
            WHERE cart_items.cart_id = :cart_id
            """
        ),[{"cart_id": cart_id}])
        
        total_potions_bought = connection.execute(sqlalchemy.text(
            """
            SELECT qty
            FROM cart_items
            WHERE cart_id = :cart_id
            """
        ), {"cart_id": cart_id}).scalar_one()

        total_price = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(qty * potions_inventory.price)
            FROM cart_items
            JOIN potions_inventory ON potions_inventory.potion_id = cart_items.potion_id
            WHERE cart_id = :cart_id
            """
        ), {"cart_id": cart_id}).scalar_one()

        connection.execute(sqlalchemy.text(
             """
            INSERT INTO gold_ledger(gold_change)
            VALUES (:total_gold)
             """
        ), [{"total_gold":total_price }])
        
      
    print(f"total_potions_bought: {total_potions_bought}, total_gold_paid: {total_price}")
    
    return {
        "total_potions_bought": total_potions_bought,
        "total_gold_paid": total_price
    }