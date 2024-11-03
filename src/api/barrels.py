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
    
    print(f"(first) barrels delivered: {barrels_delivered} order_id: {order_id}")
    
    # Define potion type mapping
    potion_type_map = {
        (1, 0, 0, 0): "red",
        (0, 1, 0, 0): "green",
        (0, 0, 1, 0): "blue",
        (0, 0, 0, 1): "dark",
    }

    gold_paid = 0
    total_cost = 0
    potion_ml = {"red": 0, "green": 0, "blue": 0, "dark": 0}

    # Update the ml (inventory) after the barrels are delivered.
    for barrel in barrels_delivered:
        total_cost += barrel.price * barrel.quantity
        potion_type_key = tuple(barrel.potion_type)

        if potion_type_key in potion_type_map:
            potion_color = potion_type_map[potion_type_key]
            potion_ml[potion_color] += barrel.ml_per_barrel * barrel.quantity
    
    # with db.engine.begin() as connection:
    #     connection.execute(sqlalchemy.text(
    #     """
    #     UPDATE global_inventory
    #     SET num_red_ml = num_red_ml + :red_ml,
    #     num_green_ml = num_green_ml + :green_ml,
    #     num_blue_ml = num_blue_ml + :blue_ml,
    #     num_dark_ml = num_dark_ml + :dark_ml,
    #     gold = gold - :gold_paid
    #     """
    # ), {
    #     'red_ml' : potion_ml["red"],
    #     'green_ml' : potion_ml["green"],
    #     'blue_ml' : potion_ml["blue"],
    #     'dark_ml' : potion_ml["dark"],
    #     'gold_paid': gold_paid
    # })

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO gold_ledger(gold_change)
            VALUES (:total_cost)
            """
        ),
        [{"total_cost": -total_cost}]
    )
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO ml_ledger(red_ml_change, green_ml_change, blue_ml_change, dark_ml_change)
            VALUES (:red_ml, :green_ml, :blue_ml, :dark_ml)
            """
        ),
        [{"red_ml": potion_ml["red"], "green_ml": potion_ml["green"], "blue_ml": potion_ml["blue"], "dark_ml": potion_ml["dark"]}]
    )

    print(f"(second) barrels delivered: {barrels_delivered} order_id: {order_id}")

    return {"message": "Delivered barrels and added ml to inventory of all potions."}

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ Purchase a new barrel for r,g,b,d if the potion inventory is low. """
    
    print(f"barrel catalog: {wholesale_catalog}")
    
    # with db.engine.begin() as connection:
    #     result = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory"))
    #     cur_gold = result.scalar()

    with db.engine.begin() as connection:
        cur_gold = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(gold_change)
            FROM gold_ledger
            """
        )).scalar_one()

    purchase_plan = []
    quantity = {barrel.sku: 0 for barrel in wholesale_catalog}

    max_attempts = 5
    attempts = 0
    print(f"Current Gold (barrels.py) before purchasing: {cur_gold}")
    # Process up to 5 times or until there is no more gold
    while cur_gold >= 99 and attempts < max_attempts: 
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

