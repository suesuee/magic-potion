import sqlalchemy
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

POTION_TYPES = {
    "red": [100,0,0,0],
    "green": [0,100,0,0],
    "blue": [0,0,100,0],
    "dark": [0,0,0,100]
}

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ Convert potions in barrels to bottles in 100ml each """
    
    # Fetch the data first to ensure we are not overwriting the existing values.
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            "SELECT num_green_potions, num_green_ml FROM global_inventory WHERE id = 1"
        ))

        row = result.fetchone()
        if row: 
            cur_num_green_potions = row[0]
            cur_num_green_ml = row[1]

        remaining_ml = 0
        for potion in potions_delivered:
            if potion.potion_type == POTION_TYPES["green"]:
                cur_num_green_ml += potion.quantity * 100 # Add ml for the delivered potions

                cur_green_potions_to_bottle = cur_num_green_ml // 100 # Return int  
                remaining_ml += cur_num_green_ml % 100 # Return remainder aka left over ml from potions to bottle

                # Update again after bottled
                cur_num_green_potions += cur_green_potions_to_bottle
                cur_num_green_ml = remaining_ml

        connection.execute(sqlalchemy.text(
            "UPDATE global_inventory SET num_green_potions = :num_green_potions, num_green_ml = :num_green_ml WHERE id = 1"
        ), {
            'num_green_potions': cur_num_green_potions,
            'num_green_ml': cur_num_green_ml
        })               

    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            "SELECT num_green_ml FROM global_inventory WHERE id = 1"
        ))

        row = result.fetchone()
        if row:
            cur_num_green_ml = row[0]

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into green potions.
    cur_green_potions_to_bottle = cur_num_green_ml // 100 # Return int
    
    if cur_green_potions_to_bottle > 0:
        return [
                {
                    "potion_type": [0, 100, 0, 0],
                    "quantity": cur_green_potions_to_bottle,
                }
            ]
    return []

if __name__ == "__main__":
    print(get_bottle_plan())