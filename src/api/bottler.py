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
        result = connection.execute(sqlalchemy.text("""
            SELECT num_green_potions, num_green_ml,
                    num_green_potions, num_green_ml
                    num_red_potions, num_red_ml,
                    num_dark_potions, num_dark_ml,
                    gold
            FROM global_inventory"""
        ))

        row = result.fetchone()
        if row:

            cur_num_red_potions = row[0]
            cur_num_red_ml = row[1]
            cur_num_green_potions = row[2]
            cur_num_green_ml = row[3]
            cur_num_blue_potions = row[4]
            cur_num_blue_ml = row[5]
            cur_num_dark_potions = row[6]
            cur_num_dark_ml = row[7]
            cur_gold = row[8]

        remaining_ml = {"red": 0, "green": 0, "blue": 0, "dark": 0}

        for potion in potions_delivered:
            if potion.potion_type == POTION_TYPES["red"]:
                cur_num_red_ml += potion.quantity * 100 # Get ml for the delivered potions

                cur_red_potions_to_bottle = cur_num_red_ml // 100 # Return int  
                remaining_ml["red"] += cur_num_red_ml % 100 # Return remainder aka left over ml from potions_to_bottle

                # Update again after bottled
                cur_num_red_potions += cur_red_potions_to_bottle
                cur_num_red_ml = remaining_ml

            elif potion.potion_type == POTION_TYPES["green"]:
                cur_num_green_ml += potion.quantity * 100 # Get ml for the delivered potions

                cur_green_potions_to_bottle = cur_num_green_ml // 100 # Return int  
                remaining_ml["green"] += cur_num_green_ml % 100 # Return remainder aka left over ml from potions_to_bottle

                # Update again after bottled
                cur_num_green_potions += cur_green_potions_to_bottle
                cur_num_green_ml = remaining_ml

            elif potion.potion_type == POTION_TYPES["blue"]:
                cur_num_blue_ml += potion.quantity * 100 # Get ml for the delivered potions

                cur_blue_potions_to_bottle = cur_num_blue_ml // 100 # Return int  
                remaining_ml["blue"] += cur_num_blue_ml % 100 # Return remainder aka left over ml from potions_to_bottle

                # Update again after bottled
                cur_num_blue_potions += cur_blue_potions_to_bottle
                cur_num_blue_ml = remaining_ml

            elif potion.potion_type == POTION_TYPES["dark"]:
                cur_num_dark_ml += potion.quantity * 100 # Get ml for the delivered potions

                cur_dark_potions_to_bottle = cur_num_dark_ml // 100 # Return int  
                remaining_ml["dark"] += cur_num_dark_ml % 100 # Return remainder aka left over ml from potions_to_bottle

                # Update again after bottled
                cur_num_dark_potions += cur_dark_potions_to_bottle
                cur_num_dark_ml = remaining_ml

        connection.execute(sqlalchemy.text(
            """
            UPDATE global_inventory 
            SET num_red_potions=:num_red_potions, num_red_ml =:num_red_ml,
                num_green_potions=:num_green_potions, num_green_ml =:num_green_ml, 
                num_blue_potions=:num_blue_potions, num_blue_ml =:num_blue_ml
                num_dark_potions=:num_dark_potions, num_dark_ml =:num_dark_ml
            """
        ), {
            'num_red_potions': cur_num_red_potions,
            'num_red_ml': cur_num_red_ml
            'num_green_potions': cur_num_green_potions,
            'num_green_ml': cur_num_green_ml
            'num_blue_potions': cur_num_blue_potions,
            'num_blue_ml': cur_num_blue_ml
            'num_dark_potions': cur_num_dark_potions,
            'num_dark_ml': cur_num_dark_ml
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
    elif cur_green_potions_to_bottle > 0:
        my_bottle_plan.append(
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": cur_green_potions_to_bottle,
            }
        )
    elif cur_blue_potions_to_bottle > 0:
        my_bottle_plan.append(
            {
                "potion_type": [0, 0, 100, 0],
                "quantity": cur_blue_potions_to_bottle,
            }
        )
    elif cur_dark_potions_to_bottle > 0:
        my_bottle_plan.append(
            {
                "potion_type": [0, 0, 0, 100],
                "quantity": cur_dark_potions_to_bottle,
            }
        )

    return my_bottle_plan if my_bottle_plan else []

if __name__ == "__main__":
    print(get_bottle_plan())