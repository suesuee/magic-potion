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

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }

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
    
    # Fetch potion details from potion_inventory
    with db.engine.begin() as connection:
        potion_result = connection.execute(sqlalchemy.text(
            "SELECT potion_id, inventory FROM potions_inventory WHERE sku = :item_sku"
        ), {"item_sku": item_sku})
        row = potion_result.fetchone()

        if not row:
            return {"success": False, "message": "Potion not found in inventory."}, 404

        potion_id, available_inventory = row

    # Ensure requested quantity is within available stock
    if cart_item.quantity < available_inventory:
        # Update or insert the cart_items record
        with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text(
                "INSERT INTO cart_items (cart_id, potion_id, qty, added_at) "
                "VALUES (:cart_id, :potion_id, :qty, now()) "
                "ON CONFLICT (cart_id, potion_id) DO UPDATE SET qty = :qty"
            ), {
                "cart_id": cart_id,
                "potion_id": potion_id,
                "qty": cart_item.quantity,
            })

    if cart_item.quantity > available_inventory:
        return {"success": False, "message": "Not enough stock to add the potion to the cart."}

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

    # Check if the cart exists
    with db.engine.begin() as connection:
        cart_items_result = connection.execute(sqlalchemy.text(
            "SELECT ci.potion_id, ci.qty, pi.sku, pi.price, pi.inventory "
            "FROM cart_items ci "
            "JOIN potions_inventory pi ON ci.potion_id = pi.potion_id "
            "WHERE ci.cart_id = :cart_id"
        ), {"cart_id": cart_id})

        cart_items = cart_items_result.fetchall()
        if not cart_items:
            return {"message": "Cart not found or is empty"}, 404

        # Fetch current gold
        gold_result = connection.execute(sqlalchemy.text(
            "SELECT gold FROM global_inventory"
        ))
        current_gold = gold_result.scalar()

    total_potions_bought = 0
    total_price = 0

    # Iterate through each item in the cart
    with db.engine.begin() as connection:
        for potion_id, quantity, sku, price_per_potion, available_inventory in cart_items:
            # Check if there is enough stock for each item
            if quantity > available_inventory:
                return {"message": f"Not enough stock for {sku}"}

            # Deduct from inventory and update the total calculations
            new_inventory = available_inventory - quantity
            total_potions_bought += quantity
            total_price += quantity * price_per_potion

            # Update potion_inventory table
            connection.execute(sqlalchemy.text(
                "UPDATE potions_inventory SET inventory = :new_inventory WHERE potion_id = :potion_id"
            ), {
                "new_inventory": new_inventory,
                "potion_id": potion_id
            })

        # Deduct the total price from the current gold
        current_gold += total_price

        print
        # Update global_inventory table for the gold
        connection.execute(sqlalchemy.text(
            "UPDATE global_inventory SET gold = :new_gold"
        ), {
            "new_gold": current_gold
        })

    print(f"total_potions_bought: {total_potions_bought}, total_gold_paid: {total_potions_bought}")
    return {
        "total_potions_bought": total_potions_bought,
        "total_gold_paid": total_price
    }