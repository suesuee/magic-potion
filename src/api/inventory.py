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
        global_inventory = connection.execute(sqlalchemy.text(
            """
            SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, gold 
            FROM global_inventory
            """
        )).first()
        total_potions = connection.execute(sqlalchemy.text(
            """
            SELECT COALESCE(SUM(inventory), 0)
            FROM potions_inventory
            """
        )).scalar()
    
    total_ml = global_inventory.num_red_ml + global_inventory.num_green_ml + global_inventory.num_blue_ml + global_inventory.num_dark_ml


    return {
        "number_of_potions": total_potions,
        "ml_in_barrels": total_ml,
        "gold": global_inventory.gold
    }

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return {
        "potion_capacity:": 0,
        "ml_capacity": 0
    }
    # with db.engine.begin() as connection:
    #     result = connection.execute(sqlalchemy.text("""
    #         SELECT potion_capacity, ml_capacity, 
    #         (num_red_potions + num_green_potions + num_blue_potions + num_dark_potions) as total_potions, 
    #         (num_red_ml + num_green_ml + num_blue_ml + num_dark_ml) as total_ml, 
    #         gold FROM global_inventory
    #     """))
    #     row = result.fetchone()

    #     if row:
    #         cur_potion_capacity = row[0]
    #         cur_ml_capacity = row[1]
    #         total_potions = row[2]
    #         total_ml = row[3]
    #         cur_gold = row[4]

    # potion_threshold = 10
    # ml_threshold = 500
    # purchase_plan = {}

    # if total_potions < cur_potion_capacity - potion_threshold and cur_gold >= 1000:
    #     purchase_plan["potion_capacity"] = 50
    #     #cur_gold -= 1000

    # if total_ml < cur_ml_capacity - ml_threshold and cur_gold >= 1000:
    #     purchase_plan["ml_capacity"] = 1000
    #     #cur_gold -= 1000

    # return purchase_plan if purchase_plan else {
    #     "potion_capacity": cur_potion_capacity,
    #     "ml_capacity": cur_ml_capacity
    # }

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
    return "OK"

    # with db.engine.begin() as connection:
    #     result = connection.execute(sqlalchemy.text(
    #         "SELECT potion_capacity, ml_capacity, gold from global_inventory"
    #     ))

    #     row = result.fetchone()
    #     if row:
    #         cur_potion_capacity = row[0]
    #         cur_ml_capacity = row[1]
    #         cur_gold = row[2]

    #     connection.execute(sqlalchemy.text(
    #         """
    #         UPDATE global_inventory 
    #         SET potion_capacity = potion_capacity + :potion_capacity,
    #         ml_capacity = ml_capacity + :ml_capacity,
    #         gold = gold - 1000
    #         """
    #     ),{
    #         'potion_capacity': capacity_purchase.potion_capacity,
    #         'ml_capacity': capacity_purchase.ml_capacity,
    #         'gold': cur_gold
    #     })


    #     return {
    #         "potion_capacity": capacity_purchase.potion_capacity,  
    #         "ml_capacity": capacity_purchase.ml_capacity           
    #     }
    # else:
    #     return {
    #         "message": "You need more gold to purchase additional capacity.",
    #         "gold_required": additional_cost,
    #         "current_gold": cur_gold,
    #         "potion_capacity": capacity_purchase.potion_capacity,  
    #         "ml_capacity": capacity_purchase.ml_capacity
  
    #     }
