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

        # for potion_delivered in potions_delivered:
        #     connection.execute(sqlalchemy.text(
        #         """
        #         UPDATE potions_inventory
        #         SET inventory = inventory + :potions_delivered
        #         WHERE potion_type = :potion_type
        #         """),
        #         {"potions_delivered": potion_delivered.quantity, "potion_type": potion_delivered.potion_type}
        #     )
        for potion_delivered in potions_delivered:
            connection.execute(sqlalchemy.text(
                """
                INSERT INTO potion_ledger(potion_change, potion_id)
                SELECT :change_of_potion, potion_id
                FROM potions_inventory
                WHERE potions_inventory.potion_type = :potion_type
                """
            ),[{"change_of_potion": potion_delivered.quantity, "potion_type": potion_delivered.potion_type}])
        
        # connection.execute(sqlalchemy.text(
        #     """
        #     UPDATE global_inventory
        #     SET num_red_ml = num_red_ml - :red_ml,
        #     num_green_ml = num_green_ml - :green_ml,
        #     num_blue_ml = num_blue_ml - :blue_ml,
        #     num_dark_ml = num_dark_ml - :dark_ml
        #     """
        # ), 
        # {"red_ml": red_ml, "green_ml": green_ml, "blue_ml": blue_ml, "dark_ml": dark_ml})    

        connection.execute(sqlalchemy.text(
            """
            INSERT INTO ml_ledger(red_ml_change, green_ml_change, blue_ml_change, dark_ml_change)
            VALUES(:red_ml, :green_ml, :blue_ml, :dark_ml )
            """
        ),[{"red_ml": -red_ml, "green_ml": -green_ml, "blue_ml": -blue_ml, "dark_ml": -dark_ml}])

    print(f"Potions delivered: {potions_delivered}, Order ID: {order_id}")
    print(f"New potions delivered quantity: {new_potions}")
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # with db.engine.begin() as connection:
    #     result = connection.execute(sqlalchemy.text(
    #         """
    #         SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml 
    #         FROM global_inventory
    #         """
    #         )
    #     )
    #     potion_data = connection.execute(sqlalchemy.text("SELECT * from potions_inventory"))

    with db.engine.begin() as connection:
        cur_red_ml = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(red_ml_change)
            FROM ml_ledger
            """
        )).scalar_one()
        cur_green_ml = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(green_ml_change)
            FROM ml_ledger
            """
        )).scalar_one()
        cur_blue_ml = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(blue_ml_change)
            FROM ml_ledger
            """
        )).scalar_one()
        cur_dark_ml = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(dark_ml_change)
            FROM ml_ledger
            """
        )).scalar_one()
        
        potion_data = connection.execute(sqlalchemy.text(
            """
            SELECT potions_inventory.potion_id, potions_inventory.sku, SUM(potion_ledger.potion_change), potions_inventory.potion_type
            FROM potions_inventory
            JOIN potion_ledger ON potions_inventory.potion_id = potion_ledger.potion_id
            GROUP BY potions_inventory.potion_id
            """
        )).fetchall()

        total_inventory = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(potion_change)
            FROM potion_ledger
            """
        )).scalar_one()

    #fetchall() gives you a list of "Row" objects
    #all() gives you ORM model instances
    #Both ways will give me the access to columns
    
    potion_list = [potion for potion in potion_data]
    print(f"get bottler plan's potion_list: {potion_list}")
    # total_potion_made = 0
    my_bottle_plan = []
    potion_quantities = {}

    for potion in potion_list:
        potion_quantities[potion.sku] = 0
        
    num_potions = len(potion_list)
    
    print(f"Number of potions: {num_potions}")
    
    while num_potions > 0:
        num_potions -= 1

        for potion in potion_list:
            print(f"Potions in the loop: {potion}")
            print(f"potion.potion_type[0]: {potion.potion_type[0]}")
            print(f"potion.potion_type[1]: {potion.potion_type[1]}")
            print(f"potion.potion_type[2]: {potion.potion_type[2]}")
            print(f"potion.potion_type[3]: {potion.potion_type[3]}")

            indv_inventory = connection.execute(sqlalchemy.text(
                            """
                            SELECT SUM(potion_change)
                            FROM potion_ledger
                            WHERE potion_ledger = :potion_id
                            """
                        ),[{"potion_id": potion.id}]).scalar_one()

            if (potion_quantities[potion.sku] + indv_inventory < 7 and
                potion.potion_type[0] <= cur_red_ml and
                potion.potion_type[1] <= cur_green_ml and
                potion.potion_type[2] <= cur_blue_ml and
                potion.potion_type[3] <= cur_dark_ml):

                cur_red_ml -= potion.potion_type[0]
                cur_green_ml -= potion.potion_type[1]
                cur_blue_ml -= potion.potion_type[2]
                cur_dark_ml -= potion.potion_type[3]

                potion_quantities[potion.sku] += 1
                
                print(f"Number of potions inside the loop: {num_potions}")
                print(f"Below are the current mls:")
                print(cur_red_ml, cur_green_ml, cur_blue_ml, cur_dark_ml)
                print(f"These are potion quantities: {potion_quantities}")
    
    for potion in potion_list:
        if potion_quantities[potion.sku] > 0:
            my_bottle_plan.append({
                "potion_type": potion.potion_type,
                "quantity": potion_quantities[potion.sku]
            })
    
    return my_bottle_plan

if __name__ == "__main__":
    print(get_bottle_plan())