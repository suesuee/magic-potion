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

    cur_red_bottles = 0
    cur_green_bottles = 0
    cur_blue_bottles = 0
    cur_dark_bottles = 0
    red_ml_remaining = 0
    green_ml_remaining = 0
    blue_ml_remaining = 0
    dark_ml_remaining = 0
            
    for potion in potions_delivered:
        quantity = potion.quantity
        # potion_type = potion.potion_type
        if potion.potion_type == POTION_TYPES["red"]: 
            cur_red_bottles += quantity
            red_ml_remaining += quantity % 100
        if potion.potion_type == POTION_TYPES["green"]: 
            cur_green_bottles += quantity
            green_ml_remaining += quantity % 100
        if potion.potion_type == POTION_TYPES["blue"]: 
            cur_blue_bottles += quantity
            blue_ml_remaining += quantity % 100
        if potion.potion_type == POTION_TYPES["dark"]:
            cur_dark_bottles += quantity
            dark_ml_remaining += quantity % 100   

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
        """
        UPDATE global_inventory 
        SET num_red_potions= num_red_potions + :cur_red_bottles, num_red_ml = num_red_ml + :red_ml_remaining,
            num_green_potions= num_green_potions + :cur_green_bottles, num_green_ml = num_green_ml + :green_ml_remaining, 
            num_blue_potions= num_blue_potions + :cur_blue_bottles, num_blue_ml = num_blue_ml + :blue_ml_remaining,
            num_dark_potions= num_dark_potions + :cur_dark_bottles, num_dark_ml = num_dark_ml + :dark_ml_remaining
        """
    ), {
        'cur_red_bottles': cur_red_bottles,
        'red_ml_remaining': red_ml_remaining,
        'cur_green_bottles': cur_green_bottles,
        'green_ml_remaining': green_ml_remaining,
        'cur_blue_bottles': cur_blue_bottles,
        'blue_ml_remaining': blue_ml_remaining,
        'cur_dark_bottles': cur_dark_bottles,
        'dark_ml_remaining': dark_ml_remaining,
    })               

    print(f"potions bottles delivered: {potions_delivered} order_id: {order_id}")

    return {'message': "Bottles delivered successfully"}

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