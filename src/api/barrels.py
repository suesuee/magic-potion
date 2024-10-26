import sqlalchemy
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ Updates the inventory based on delivered barrels. """
    print(f"barrels delivered: {barrels_delivered}")
       # Define potion type mapping
    potion_type_map = {
        (1, 0, 0, 0): "red",
        (0, 1, 0, 0): "green",
        (0, 0, 1, 0): "blue",
        (0, 0, 0, 1): "dark",
    }

    gold_paid = 0
    potion_ml = {"red": 0, "green": 0, "blue": 0, "dark": 0}

    # Update the ml (inventory) after the barrels are delivered.
    for barrel in barrels_delivered:
        gold_paid += barrel.price * barrel.quantity
        potion_type_key = tuple(barrel.potion_type)

        if potion_type_key in potion_type_map:
            potion_color = potion_type_map[potion_type_key]
            potion_ml[potion_color] += barrel.ml_per_barrel * barrel.quantity
        else:
            raise ValueError("Invalid potion type")
    
    with db.engine.begin() as connection:
    # Then we update the GI table with the new values
        connection.execute(sqlalchemy.text(
        """UPDATE global_inventory
            SET num_red_ml = num_red_ml + :red_ml,
            num_green_ml = num_green_ml + :green_ml,
            num_blue_ml = num_blue_ml + :blue_ml,
            num_dark_ml = num_dark_ml + :dark_ml,
            gold = gold - :gold_paid
            """
    ), {
        'red_ml' : potion_ml["red"],
        'green_ml' : potion_ml["green"],
        'blue_ml' : potion_ml["blue"],
        'dark_ml' : potion_ml["dark"],
        'gold_paid': gold_paid
    })

    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")

    return {"message": "Delivered barrels and added ml to inventory of all potions."}

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    # helps decide when and what potion barrels to purchase from a supplier 
    # (wholesaler) based on your current inventory and available gold.
    """ Purchase a new barrel for r,g,b,d if the potion inventory is low. """
    print(f"barrel catalog: {wholesale_catalog}")
    
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory"))
        cur_gold = result.scalar()

    purchase_plan = []
    quantity = {barrel.sku: 0 for barrel in wholesale_catalog}

    max_attempts = 5
    attempts = 0
    print(f"Current Gold (barrels.py) before purchasing: {cur_gold}")
    # Purchase logic for different sizes
    # Process up to 10 times or until there is no more gold
    while cur_gold >= 0 and attempts < max_attempts: 
        attempts += 1
        for barrel in wholesale_catalog:
            if cur_gold >= barrel.price:
                if 'SMALL' in barrel.sku:
                    quantity[barrel.sku] += 1
                    barrel.quantity -= 1
                    cur_gold -= barrel.price
    
    print(f"Current Gold (barrels.py): {cur_gold}")
    
    for barrel in wholesale_catalog:
        if(quantity[barrel.sku] != 0):
            purchase_plan.append(
                {
                    "sku":barrel.sku,
                    "quantity": quantity[barrel.sku]
                }
            )
    print(f"let's see my purchase plan: {purchase_plan}")
    return purchase_plan if purchase_plan else [] # Return an empty plan if purchase is not needed

