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
            num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, gold FROM global_inventory
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
            cur_gold = row[8]

    return {
        "red_potions": cur_num_red_potions, 
        "green_potions": cur_num_green_potions, 
        "blue_potions": cur_num_blue_potions, 
        "dark_potions": cur_num_dark_potions, 
        "red_ml": cur_num_red_ml,
        "green_ml": cur_num_green_ml,
        "blue_ml": cur_num_blue_ml,
        "dark_ml": cur_num_dark_ml,
        "gold": cur_gold
    }

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return {
        "potion_capacity": 50,
        "ml_capacity": 10000
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
    cost_per_unit = 1000
    additional_cost = (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * cost_per_unit

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            "SELECT gold from global_inventory"
        ))

        row = result.fetchone()
        if row:
            cur_gold = row[0]
        if cur_gold >= additional_cost:
            cur_gold -= additional_cost

            connection.execute(sqlalchemy.text(
                "UPDATE global_inventory SET gold = :gold"
            ),{'gold': cur_gold})
            return {
                "message": f"Capacity updated. {capacity_purchase.potion_capacity} potion capacity "
                        f"and {capacity_purchase.ml_capacity} ml capacity added.",
                "gold_remaining": cur_gold,
                "potion_capacity": capacity_purchase.potion_capacity,  
                "ml_capacity": capacity_purchase.ml_capacity           
            }
        else:
            return {
                "message": "You need more gold to purchase additional capacity.",
                "gold_required": additional_cost,
                "current_gold": cur_gold,
                "potion_capacity": capacity_purchase.potion_capacity,  
                "ml_capacity": capacity_purchase.ml_capacity
  
            }
