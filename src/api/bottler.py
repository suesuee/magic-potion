import sqlalchemy
from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
from src import database as db
import random

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
    print("CALLED post_deliver_bottles().")

    with db.engine.begin() as connection:
        total_new_potions = sum(potion.quantity for potion in potions_delivered)
        red_ml_used = sum(potion.quantity * potion.potion_type[0] for potion in potions_delivered)
        green_ml_used = sum(potion.quantity * potion.potion_type[1] for potion in potions_delivered)
        blue_ml_used = sum(potion.quantity * potion.potion_type[2] for potion in potions_delivered)
        dark_ml_used = sum(potion.quantity * potion.potion_type[3] for potion in potions_delivered)

        for potion_delivered in potions_delivered:
            connection.execute(sqlalchemy.text(
                """
                INSERT INTO potion_ledger(potion_change, potion_id)
                SELECT :change_of_potion, potion_id
                FROM potions_inventory
                WHERE num_red_ml = :num_red_ml
                  AND num_green_ml = :num_green_ml
                  AND num_blue_ml = :num_blue_ml
                  AND num_dark_ml = :num_dark_ml
                """
            ),{"change_of_potion": potion_delivered.quantity, 
                "num_red_ml": potion_delivered.potion_type[0],
                "num_green_ml": potion_delivered.potion_type[1],
                "num_blue_ml": potion_delivered.potion_type[2],
                "num_dark_ml": potion_delivered.potion_type[3]
            })   

        connection.execute(sqlalchemy.text(
            """
            INSERT INTO ml_ledger(red_ml_change, green_ml_change, blue_ml_change, dark_ml_change)
            VALUES(:red_ml, :green_ml, :blue_ml, :dark_ml )
            """
        ),[{"red_ml": -red_ml_used, "green_ml": -green_ml_used, "blue_ml": -blue_ml_used, "dark_ml": -dark_ml_used}])

    print(f"Potions delivered: {potions_delivered}, Order ID: {order_id}")
    print(f"New potions delivered quantity: {total_new_potions}")
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    print("CALLED get_bottle_plan().")

    with db.engine.begin() as connection:
        ml_resources = connection.execute(sqlalchemy.text(
            """
            SELECT 
                SUM(red_ml_change) AS red_ml,
                SUM(green_ml_change) AS green_ml,
                SUM(blue_ml_change) AS blue_ml,
                SUM(dark_ml_change) AS dark_ml
            FROM ml_ledger
            """
        )).fetchone()

    red_ml = ml_resources.red_ml or 0
    green_ml = ml_resources.green_ml or 0
    blue_ml = ml_resources.blue_ml or 0
    dark_ml = ml_resources.dark_ml or 0

    print()
    print(f"red_ml from database: {red_ml}")
    print(f"green_ml from database: {green_ml}")
    print(f"blue_ml from database: {blue_ml}")
    print(f"dark_ml from database: {dark_ml}")

    with db.engine.begin() as connection:
        capacity_data = connection.execute(sqlalchemy.text(
            """
            SELECT potion_c FROM capacities LIMIT 1
            """
        )).fetchone()
        potion_capacity = capacity_data.potion_c
        #potion_capacity = 200 # to change back
        production_limit = int(potion_capacity * 0.95)
        base_cap_percentage = 0.1  # Base cap for each potion
        max_inventory_per_potion = 5 # to change back
        # max_per_potion_type = int(potion_capacity * 0.25)  # 25% limit per potion type - uncomment when i have more potion capacity

        print()
        print(f"potion capacity: {potion_capacity}")
        print(f"production_limit: {production_limit}")
        print(f"base_cap_percentage: {base_cap_percentage}")
        print(f"max_inventory_per_potion: {max_inventory_per_potion}")
        # print(f"max per potion type: {max_per_potion_type}")
    
    with db.engine.begin() as connection:
        potion_data = connection.execute(sqlalchemy.text(
            """
            SELECT potions_inventory.potion_id AS id, potions_inventory.sku, 
                SUM(potion_ledger.potion_change) AS inventory, potions_inventory.potion_type, 
                potions_inventory.num_red_ml, potions_inventory.num_green_ml, 
                potions_inventory.num_blue_ml, potions_inventory.num_dark_ml, 
                potions_inventory.price
            FROM potions_inventory
            LEFT JOIN potion_ledger ON potions_inventory.potion_id = potion_ledger.potion_id
            GROUP BY potions_inventory.potion_id
            """
        )).fetchall()

        total_inventory = connection.execute(sqlalchemy.text(
            """
            SELECT COALESCE(SUM(potion_change), 0)
            FROM potion_ledger
            """
        )).scalar() or 0

    print()
    print(f"total_inventory from database: {total_inventory}")

    # Sort potions:
    # 1. Special case [0, 0, 0, 100] is prioritized first.
    # 2. Mixed potions (more non-zero MLs) are prioritized over single ML potions.
    # 3. Higher price is prioritized.
    # 4. Randomization for tie-breaking.
    sorted_potions = sorted(
        potion_data,
        key=lambda p: (
            0 if p.num_dark_ml > 0 else 1,  # Special case
            -sum(1 for ml in [p.num_red_ml, p.num_green_ml, p.num_blue_ml, p.num_dark_ml] if ml > 0),  # Count of non-zero MLs
            p.price,  # Price in descending order
            random.random()  # Random tie-breaking
        )
    )
    print()
    print(f"sorted_potions: {sorted_potions}")
    
    total_potion_made = 0
    my_bottle_plan = []
    potion_quantities = {potion.sku: 0 for potion in sorted_potions}

    
    random.shuffle(sorted_potions)
    for potion in sorted_potions:
        
        # Skip production if total inventory for this potion already exceeds the max inventory cap
        current_inventory = potion.inventory or 0
        if current_inventory >= max_inventory_per_potion:
            print()
            print(f"Skipping {potion.sku} as it exceeds the max inventory limit of {max_inventory_per_potion}")
            continue
            
        #production_limit = int(potion_capacity * 0.8)
        #base_cap_percentage = 0.1  # Base cap for each potion
        #max_inventory_per_potion = 5
        # Determine base cap using percentage of total capacity
        base_cap = int(potion_capacity * base_cap_percentage)

        print()
        print(f"current inventory: {current_inventory}")
        print(f"potion_capacity * 0.25: {potion_capacity * 0.25}")
        # Adjust cap based on current inventory levels using tiered logic
        if total_inventory < potion_capacity * 0.25:
            tier_cap = int(base_cap * 1.5)  # Increase cap by 50% for low inventory
        elif total_inventory < potion_capacity * 0.75:
            tier_cap = base_cap  # Maintain base cap for medium inventory
        else:
            tier_cap = int(base_cap * 0.5)  # Decrease cap by 50% for high inventory

        print(f"Tier cap: {tier_cap}")

        max_bottles_possible = min(
            red_ml // potion.num_red_ml if potion.num_red_ml > 0 else float('inf'),
            green_ml // potion.num_green_ml if potion.num_green_ml > 0 else float('inf'),
            blue_ml // potion.num_blue_ml if potion.num_blue_ml > 0 else float('inf'),
            dark_ml // potion.num_dark_ml if potion.num_dark_ml > 0 else float ('inf')
        )
        print()
        print(f"potion color: {potion.sku}")
        print()
        print(f"red_ml // potion.num_red_ml: {red_ml // potion.num_red_ml if potion.num_red_ml > 0 else 0}")
        print(f"green_ml // potion.num_green_ml: {green_ml // potion.num_green_ml if potion.num_green_ml > 0 else 0}")
        print(f"blue_ml // potion.num_blue_ml: {blue_ml // potion.num_blue_ml if potion.num_blue_ml > 0 else 0}")
        print(f"dark_ml // potion.num_dark_ml: {dark_ml // potion.num_dark_ml if potion.num_dark_ml > 0 else 0}")
        print(f"max_bottles_possible: {max_bottles_possible}")

        # Limit production to the per-potion cap, available capacity, and max inventory
        target_quantity = min(
            max_bottles_possible, 
            production_limit - total_potion_made, 
            tier_cap - potion_quantities[potion.sku]
        )
    
        print(f"potion_quantities[potion.sku] before if: {potion_quantities[potion.sku]}")
        print(f"production limit target_quantity: {target_quantity}")

        if total_potion_made + target_quantity > production_limit:
            target_quantity = production_limit - total_potion_made
    
        print(f"TOTAL POTION MADE: {total_potion_made}")
        print(f"final target_quantity: {target_quantity}")
    
        # If target_quantity is zero, skip production
        if target_quantity <= 0:
            continue

        red_ml -= potion.num_red_ml * target_quantity
        green_ml -= potion.num_green_ml * target_quantity
        blue_ml -= potion.num_blue_ml * target_quantity
        dark_ml -= potion.num_dark_ml * target_quantity

        potion_quantities[potion.sku] += target_quantity # adding target_quantity directly no looping required
        print(f"potion_quantities[potion.sku] after if: {potion_quantities[potion.sku]}")
        total_potion_made += target_quantity
        #production_limit -= target_quantity

        print()
        print(f"TOTAL POTION MADE after the if target_quantity > 0: {total_potion_made}")
        print(f"TOTAL_INVENTORY: {total_inventory}")
        print(f"production_limit before break 2: {production_limit}")

        print()

        if total_potion_made + total_inventory >= production_limit:
            print(f"total_potion_made + total_inventory  >= production_limit so breaking 2")
            break
        
        print()
        print(f"TOTAL POTION MADE after the if target_quantity > 0: {total_potion_made}")
        print(f"TOTAL_INVENTORY: {total_inventory}")
        print(f"production_limit after break 2: {production_limit}")

        my_bottle_plan.append({
            "potion_type": [
                potion.num_red_ml,
                potion.num_green_ml,
                potion.num_blue_ml,
                potion.num_dark_ml
            ],
            "quantity": target_quantity
        })
        print()
        print(f"my_bottle_plan: {my_bottle_plan}")
            

    print()
    print(f"my_final_bottle_plan: {my_bottle_plan}")
    #fetchall() gives you a list of "Row" objects
    #all() gives you ORM model instances
    #Both ways will give me the access to columns
    
    return my_bottle_plan

if __name__ == "__main__":
    print(get_bottle_plan())