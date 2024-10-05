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
        result = connection.execute(sqlalchemy.text(
            "SELECT num_green_potions, num_green_ml, gold FROM global_inventory WHERE id = 1"
        ))

        row = result.fetchone()
        if row: 
            cur_num_green_potions = row[0]
            cur_num_green_ml = row[1]
            cur_gold = row[2]

    return {
        "number_of_potions": cur_num_green_potions, 
        "ml_in_barrels": cur_num_green_ml, 
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
        "potion_capacity": 0,
        "ml_capacity": 0
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

    return "OK"
