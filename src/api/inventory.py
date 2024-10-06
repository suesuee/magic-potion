import math
import sqlalchemy
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """ Get what we have currently from the database """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT num_red_potions, num_green_potions, num_blue_potions, num_dark_potions,
            num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, potion_capacity, ml_capacity, gold FROM global_inventory
        """
        ))

        row = result.fetchone()
        if row: 
            cur_num_red_potions = row[0]
            cur_num_green_potions = row[1]
            cur_num_blue_potions = row[2]
            cur_num_dark_potions = row[3]
            cur_num_red_ml = row[4]
            cur_num_green_ml = row[5]
            cur_num_blue_ml = row[6]
            cur_num_dark_ml = row[7]
            cur_potion_capacity = row[8]
            cur_ml_capacity = row[9]
            cur_gold = row[10]

    return {
        "red_potions": cur_num_red_potions, 
        "green_potions": cur_num_green_potions, 
        "blue_potions": cur_num_blue_potions, 
        "dark_potions": cur_num_dark_potions, 
        "red_ml": cur_num_red_ml,
        "green_ml": cur_num_green_ml,
        "blue_ml": cur_num_blue_ml,
        "dark_ml": cur_num_dark_ml,
        "potion_capacity": cur_potion_capacity,
        "ml_capacity": cur_ml_capacity,
        "gold": cur_gold
    }

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT potion_capacity, ml_capacity, 
            (num_red_potions + num_green_potions + num_blue_potions + num_dark_potions) as total_potions, 
            (num_red_ml + num_green_ml + num_blue_ml + num_dark_ml) as total_ml, 
            gold FROM global_inventory
        """))
        row = result.fetchone()

        if row:
            cur_potion_capacity = row[0]
            cur_ml_capacity = row[1]
            total_potions = row[2]
            total_ml = row[3]
            cur_gold = row[4]

    potion_threshold = 10
    ml_threshold = 500
    purchase_plan = {}

    if total_potions < cur_potion_capacity - potion_threshold and cur_gold >= 1000:
        purchase_plan["potion_capacity"] = 50
        #cur_gold -= 1000

    if total_ml < cur_ml_capacity - ml_threshold and cur_gold >= 1000:
        purchase_plan["ml_capacity"] = 1000
        #cur_gold -= 1000

    return purchase_plan if purchase_plan else {
        "message": "No additional capacity needed",
        "potion_capacity": cur_potion_capacity,
        "ml_capacity": cur_ml_capacity,
        "gold_remaining": cur_gold
    }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            "SELECT potion_capacity, ml_capacity, gold from global_inventory"
        ))

        row = result.fetchone()
        if row:
            cur_potion_capacity = row[0],
            cur_ml_capacity = row[1],
            cur_gold = row[2]

        connection.execute(sqlalchemy.text(
            """
            UPDATE global_inventory 
            SET potion_capacity = potion_capacity + :potion_capacity,
            ml_capacity = ml_capacity + :ml_capacity,
            gold = 1000 - :gold"""
        ),{
            'potion_capacity': capacity_purchase.potion_capacity,
            'ml_capacity': capacity_purchase.ml_capacity,
            'gold': cur_gold
        })


        return {
            "message": f"Capacity updated. {capacity_purchase.potion_capacity} potion capacity "
                    f"and {capacity_purchase.ml_capacity} ml capacity added.",
            "gold_remaining": cur_gold,
            "potion_capacity": capacity_purchase.potion_capacity,  
            "ml_capacity": capacity_purchase.ml_capacity           
        }
    # else:
    #     return {
    #         "message": "You need more gold to purchase additional capacity.",
    #         "gold_required": additional_cost,
    #         "current_gold": cur_gold,
    #         "potion_capacity": capacity_purchase.potion_capacity,  
    #         "ml_capacity": capacity_purchase.ml_capacity
  
    #     }
