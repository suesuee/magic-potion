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
    
    # Fetch the data first to ensure we are not overwriting the existing values.
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            "SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, gold FROM global_inventory"
        ))
        
        row = result.fetchone()
        if row:
            cur_num_red_ml = row[0]
            cur_num_green_ml = row[1]
            cur_num_blue_ml = row[2]
            cur_num_dark_ml = row[3]
            cur_gold = row[4]

        # Update the ml (inventory) after the barrels are delivered.
        for barrel in barrels_delivered:
            if "RED" in barrel.sku.upper():
                cur_num_red_ml += barrel.ml_per_barrel * barrel.quantity
                cur_gold -= barrel.price * barrel.quantity
            elif "GREEN" in barrel.sku.upper():
                cur_num_green_ml += barrel.ml_per_barrel * barrel.quantity
                cur_gold -= barrel.price * barrel.quantity
            elif "BLUE" in barrel.sku.upper():
                cur_num_blue_ml += barrel.ml_per_barrel * barrel.quantity
                cur_gold -= barrel.price * barrel.quantity
            elif "DARK" in barrel.sku.upper():
                cur_num_dark_ml += barrel.ml_per_barrel * barrel.quantity
                cur_gold -= barrel.price * barrel.quantity
            
        else:
            print(f"Not enough gold to buy {barrel.sku}.Not buying.")
        
        
        # Then we update the GI table with the new values
        connection.execute(sqlalchemy.text(
            """UPDATE global_inventory
                SET num_red_ml=:num_red_ml,
                num_green_ml=:num_green_ml,
                num_blue_ml=:num_blue_ml,
                num_dark_ml=:num_dark_ml,
                gold=:gold
                """
        ), {
            'num_red_ml' : cur_num_red_ml,
            'num_green_ml' : cur_num_green_ml,
            'num_blue_ml' : cur_num_blue_ml,
            'num_dark_ml' : cur_num_dark_ml,
            'gold': cur_gold
        })

    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")

    return {"message": "Delivered barrels and added ml to inventory of all potions."}

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    # helps decide when and what potion barrels to purchase from a supplier 
    # (wholesaler) based on your current inventory and available gold.
    """ Purchase a new barrel for r,g,b,d if the potion inventory is low. """
    print(wholesale_catalog)
    
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            "SELECT num_red_potions, num_green_potions, num_blue_potions, num_dark_potions, gold FROM global_inventory"
        ))
    
        row = result.fetchone()
        if row:
            cur_num_red_potions = row[0]
            cur_num_green_potions = row[1]
            cur_num_blue_potions = row[2]
            cur_num_dark_potions = row[3]
            cur_gold = row[4]

    purchase_plan = []
    purchased_skus = set()

    # Purchase logic for different sizes
    for barrel in wholesale_catalog:
        if barrel.sku.upper() in purchased_skus:
            continue # Skip
        # For Red Potions
        if "RED" in barrel.sku.upper() and cur_num_red_potions < 10 and cur_gold >= barrel.price:
            purchase_plan.append({"sku": "SMALL_RED_BARREL", "quantity": 1})
            purchased_skus.add("SMALL_RED_BARREL")
        # For Green Potions
        elif "GREEN" in barrel.sku.upper() and cur_num_green_potions < 10 and cur_gold >= barrel.price:
            purchase_plan.append({"sku": "SMALL_GREEN_BARREL", "quantity": 1})
            purchased_skus.add("SMALL_GREEN_BARREL")
        # For Blue Potions
        elif "BLUE" in barrel.sku.upper() and cur_num_blue_potions < 10 and cur_gold >= barrel.price:
            purchase_plan.append({"sku": "SMALL_BLUE_BARREL", "quantity": 1})
            purchased_skus.add("SMALL_BLUE_BARREL")
        # For Dark Potions
        elif "DARK" in barrel.sku.upper() and cur_num_dark_potions < 10 and cur_gold >= barrel.price:
            purchase_plan.append({"sku": "SMALL_DARK_BARREL", "quantity": 1})
            purchased_skus.add("SMALL_DARK_BARREL")

    return purchase_plan if purchase_plan else [] # Return an empty plan if purchase is not needed

