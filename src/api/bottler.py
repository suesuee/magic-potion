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
    

    # Fetch the current potion quantities and ml from the database
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            "SELECT num_red_potions, num_red_ml, num_green_potions, num_green_ml, "
            "num_blue_potions, num_blue_ml, num_dark_potions, num_dark_ml "
            "FROM global_inventory"
        ))

        row = result.fetchone()
        if row: 
            cur_num_red_potions, cur_num_red_ml, \
            cur_num_green_potions, cur_num_green_ml, \
            cur_num_blue_potions, cur_num_blue_ml, \
            cur_num_dark_potions, cur_num_dark_ml = row

        remaining_ml_red = 0
        remaining_ml_green = 0
        remaining_ml_blue = 0
        remaining_ml_dark = 0
        # Loop through each potion delivered and update the inventory accordingly
        for potion in potions_delivered:
            if potion.potion_type == POTION_TYPES["red"]:
                cur_num_red_ml += potion.quantity * 100
                cur_red_potions_to_bottle = cur_num_red_ml // 100
                remaining_ml_red = cur_num_red_ml % 100
                cur_num_red_potions += cur_red_potions_to_bottle
                cur_num_red_ml = remaining_ml_red

            elif potion.potion_type == POTION_TYPES["green"]:
                cur_num_green_ml += potion.quantity * 100
                cur_green_potions_to_bottle = cur_num_green_ml // 100
                remaining_ml_green = cur_num_green_ml % 100
                cur_num_green_potions += cur_green_potions_to_bottle
                cur_num_green_ml = remaining_ml_green

            elif potion.potion_type == POTION_TYPES["blue"]:
                cur_num_blue_ml += potion.quantity * 100
                cur_blue_potions_to_bottle = cur_num_blue_ml // 100
                remaining_ml_blue = cur_num_blue_ml % 100
                cur_num_blue_potions += cur_blue_potions_to_bottle
                cur_num_blue_ml = remaining_ml_blue

            elif potion.potion_type == POTION_TYPES["dark"]:
                cur_num_dark_ml += potion.quantity * 100
                cur_dark_potions_to_bottle = cur_num_dark_ml // 100
                remaining_ml_dark = cur_num_dark_ml % 100
                cur_num_dark_potions += cur_dark_potions_to_bottle
                cur_num_dark_ml = remaining_ml_dark

        # Update the database with the new potion and ml counts
        connection.execute(sqlalchemy.text(
            """
            UPDATE global_inventory SET 
            num_red_potions = :num_red_potions, num_red_ml = :num_red_ml, 
            num_green_potions = :num_green_potions, num_green_ml = :num_green_ml, 
            num_blue_potions = :num_blue_potions, num_blue_ml = :num_blue_ml, 
            num_dark_potions = :num_dark_potions, num_dark_ml = :num_dark_ml 
            """
        ), {
            'num_red_potions': cur_num_red_potions,
            'num_red_ml': cur_num_red_ml,
            'num_green_potions': cur_num_green_potions,
            'num_green_ml': cur_num_green_ml,
            'num_blue_potions': cur_num_blue_potions,
            'num_blue_ml': cur_num_blue_ml,
            'num_dark_potions': cur_num_dark_potions,
            'num_dark_ml': cur_num_dark_ml
        })               

    print(f"Potions delivered: {potions_delivered}, Order ID: {order_id}")
    return "OK"


@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            "SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml FROM global_inventory"
        ))

        row = result.fetchone()
        if row:
            cur_num_red_ml = row[0]
            cur_num_green_ml = row[1]
            cur_num_blue_ml = row[2]
            cur_num_dark_ml = row[3]

    # Each bottle has a quantity of what proportion of red, blue, and green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into green potions.
    cur_red_potions_to_bottle = cur_num_red_ml // 100 # Return int
    cur_green_potions_to_bottle = cur_num_green_ml // 100
    cur_blue_potions_to_bottle = cur_num_blue_ml // 100
    cur_dark_potions_to_bottle = cur_num_dark_ml // 100

    my_bottle_plan = []
    
    if cur_red_potions_to_bottle > 0:
        my_bottle_plan.append(
            {
                "potion_type": [100, 0, 0, 0],
                "quantity": cur_red_potions_to_bottle,
            }
        )
    if cur_green_potions_to_bottle > 0:
        my_bottle_plan.append(
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": cur_green_potions_to_bottle,
            }
        )
    if cur_blue_potions_to_bottle > 0:
        my_bottle_plan.append(
            {
                "potion_type": [0, 0, 100, 0],
                "quantity": cur_blue_potions_to_bottle,
            }
        )
    if cur_dark_potions_to_bottle > 0:
        my_bottle_plan.append(
            {
                "potion_type": [0, 0, 0, 100],
                "quantity": cur_dark_potions_to_bottle,
            }
        )

    return my_bottle_plan if my_bottle_plan else []

if __name__ == "__main__":
    print(get_bottle_plan())