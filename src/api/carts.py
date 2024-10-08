import sqlalchemy
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

cart_id = 0
cart_dict = {}

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

    return {
        'success': True,  # or False, depending on your logic
        'message': f"Customer who visited: {[customer.customer_name for customer in customers]}"
    }


@router.post("/")
def create_cart(new_cart: Customer):
    """ Create a cart to store the quantity"""

    global cart_id
    cart_id += 1
    cart_dict[cart_id] = {}
    print(new_cart.customer_name, new_cart.character_class)
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
    
    if cart_id not in cart_dict:
        return {"success": False, "message": "Cart not found"}, 404

    cart = cart_dict[cart_id]
    
# How it's gonna work
#     cart_dict = {
#     1: {
#         "RED_POTION_0": 2,
#         "GREEN_POTION_0": 3
#     }
# }


    # Fetch potion quantities from global_inventory
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            "SELECT num_red_potions, num_green_potions, num_blue_potions, num_dark_potions FROM global_inventory"
        ))
        row = result.fetchone()
        if row:
            cur_num_red_potions, cur_num_green_potions, cur_num_blue_potions, cur_num_dark_potions = row
    
    # Check if the quantity added is within available stock
    if item_sku == "RED_POTION_0" and cart_item.quantity <= cur_num_red_potions:
        cart[item_sku] = cart_item.quantity
        return {"success": True, "message": "Potion added to cart", "quantity": cart_item.quantity}
    elif item_sku == "GREEN_POTION_0" and cart_item.quantity <= cur_num_green_potions:
        cart[item_sku] = cart_item.quantity
        return {"success": True, "message": "Potion added to cart", "quantity": cart_item.quantity}
    elif item_sku == "BLUE_POTION_0" and cart_item.quantity <= cur_num_blue_potions:
        cart[item_sku] = cart_item.quantity
        return {"success": True, "message": "Potion added to cart", "quantity": cart_item.quantity}
    elif item_sku == "DARK_POTION_0" and cart_item.quantity <= cur_num_dark_potions:
        cart[item_sku] = cart_item.quantity
        return {"success": True, "message": "Potion added to cart", "quantity": cart_item.quantity}
    else:
        return {"success": False, "message": "Failure. Don't add more than available stock."}
    
    # with db.engine.begin() as connection:
    #     result = connection.execute(sqlalchemy.text(
    #         "SELECT num_red_potions, num_green_potions, num_blue_potions, num_dark_potions FROM global_inventory"
    #     ))
    #     row = result.fetchone()
    #     if row:

    #         cur_num_red_potions = row[0]
    #         cur_num_green_potions = row[1]
    #         cur_num_blue_potions = row[2]
    #         cur_num_dark_potions = row[3]

    # # Check the # of items customer added to cart is not more than available potions in the inventory
    # if cart_item.quantity <= cur_num_red_potions:
    #     cart_dict[cart_id] = cart_item.quantity
    # elif cart_item.quantity <= cur_num_green_potions:
    #     cart_dict[cart_id] = cart_item.quantity
    # elif cart_item.quantity <= cur_num_blue_potions:
    #     cart_dict[cart_id] = cart_item.quantity
    # elif cart_item.quantity <= cur_num_dark_potions:
    #     cart_dict[cart_id] = cart_item.quantity

    #     # can't use f formatting string here in JSON
    #     return {"message": "Success", "total_potions_bought": quantity, "total_gold_paid": price}
    # else:
    #     return {"Message": "Failure. Don't add more than we have!", "Current green potions available:" : cur_num_green_potions}

class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ Make sure if potions are in the inventory before checking out """

    if cart_id not in cart_dict:
        return {"message": "Cart not found"}, 404
    
    cart = cart_dict[cart_id]
    total_potions_bought = 0
    total_price = 0

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            "SELECT num_red_potions, num_green_potions, num_blue_potions, num_dark_potions, gold FROM global_inventory"
        ))

        row = result.fetchone()
        if row:  # Ensure that the row is not None
            cur_num_red_potions = row[0]  # Access the values directly from the row
            cur_num_green_potions = row[1]
            cur_num_blue_potions = row[2]
            cur_num_dark_potions = row[3]
            cur_gold = row[4]

        for item_sku, quantity in cart.items():
            if item_sku == "RED_POTION_0" and quantity <= cur_num_red_potions:
                cur_num_red_potions -= quantity
                cur_gold += quantity * 50
                total_potions_bought += quantity
                total_price += quantity * 50  # Assuming potion price is 50
            elif item_sku == "GREEN_POTION_0" and quantity <= cur_num_green_potions:
                cur_num_green_potions -= quantity
                cur_gold += quantity * 50
                total_potions_bought += quantity
                total_price += quantity * 50
            elif item_sku == "BLUE_POTION_0" and quantity <= cur_num_blue_potions:
                cur_num_blue_potions -= quantity
                cur_gold += quantity * 50
                total_potions_bought += quantity
                total_price += quantity * 60
            elif item_sku == "DARK_POTION_0" and quantity <= cur_num_dark_potions:
                cur_num_dark_potions -= quantity
                cur_gold += quantity * 50
                total_potions_bought += quantity
                total_price += quantity * 50
            else:
                return {"message": f"Not enough stock for {item_sku}"}

        # Update global_inventory with new potion quantities and gold
        cur_gold += total_price
        connection.execute(sqlalchemy.text(
            """UPDATE global_inventory 
               SET num_red_potions = :num_red_potions, 
                   num_green_potions = :num_green_potions, 
                   num_blue_potions = :num_blue_potions, 
                   num_dark_potions = :num_dark_potions,
                   gold = :gold
               """
        ), {
            'num_red_potions': cur_num_red_potions,
            'num_green_potions': cur_num_green_potions,
            'num_blue_potions': cur_num_blue_potions,
            'num_dark_potions': cur_num_dark_potions,
            'gold': cur_gold
        })

    if cart_id in cart_dict:
        del cart_dict[cart_id]


    return {
        "total_potions_bought": total_potions_bought, 
        "total_gold_paid": total_price
        }