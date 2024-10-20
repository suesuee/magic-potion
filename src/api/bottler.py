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

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ Convert potions in barrels to bottles in 100ml each """

    if not potions_delivered:
        return "No potions delivered."
    
    with db.engine.begin() as connection:
        new_potions = sum(potion.quantity for potion in potions_delivered)
        red_ml = sum(potion.quantity * potion.potion_type[0] for potion in potions_delivered)
        green_ml = sum(potion.quantity * potion.potion_type[1] for potion in potions_delivered)
        blue_ml = sum(potion.quantity * potion.potion_type[2] for potion in potions_delivered)
        dark_ml = sum(potion.quantity * potion.potion_type[3] for potion in potions_delivered)

        for potion in potions_delivered:
            connection.execute(sqlalchemy.text(
                """
                UPDATE potions
                SET inventory = inventory + :new_potions
                WHERE potion_type = :potion_type
                """),
                [{"new_potions": potion.quantity, "potion_type": potion.potion_type}]
            )

        connection.execute(sqlalchemy.text(
            """
            UPDATE global_inventory
            SET num_red_ml = num_red_ml - :red_ml,
            num_green_ml = num_green_ml - :green_ml,
            num_blue_ml = num_blue_ml - :blue_ml,
            num_dark_ml = num_dark_ml - :dark_ml,
            """
        ), 
        [{"red_ml": red_ml, "green_ml": green_ml, "blue_ml": blue_ml, "dark_ml": dark_ml}]
        )    

    print(f"Potions delivered: {potions_delivered}, Order ID: {order_id}")
    return "OK"


@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml FROM global_inventory"))
        potion_data = connection.execute(sqlalchemy.text("SELECT * from potions_inventory"))

    global_inventory = result.first()
    cur_red_ml, cur_green_ml, cur_blue_ml, cur_dark_ml = global_inventory
    potion_list = [potion for potion in potion_data]
    # total_potion_made = 0
    my_bottle_plan = []
    potion_quantities = {}

    for potion in potion_list:
        potion_quantities[potion.sku] = 0
        total_potion_made += potion.inventory
    num_potions = len(potion_list)
    count = 0;
    while True:
        can_produce_any = False
        for potion in potion_list:
            if (potion_quantities[potion.sku] + potion.inventory < 40 and
                potion.potion_type[0] <= cur_red_ml and
                potion.potion_type[1] <= cur_green_ml and
                potion.potion_type[2] <= cur_blue_ml and
                potion.potion_type[3] <= cur_dark_ml):

                cur_red_ml -= potion.potion_type[0]
                cur_green_ml -= potion.potion_type[1]
                cur_blue_ml -= potion.potion_type[2]
                cur_dark_ml -= potion.potion_type[3]

                potion_quantities[potion.sku] += 1
                # total_potion_made += 1

                can_produce_any = True

        if not can_produce_any: 
            break
    
    for potion in potion_list:
        if potion_quantities[potion.sku] > 0:
            my_bottle_plan.append({
                "potion_type": potion.potion_type,
                "quantity": potion_quantities[potion.sku]
            })
    
    return my_bottle_plan

if __name__ == "__main__":
    print(get_bottle_plan())