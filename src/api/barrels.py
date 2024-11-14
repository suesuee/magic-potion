import sqlalchemy
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
from src import database as db
import random

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ Updates the inventory based on delivered barrels. """
    print("CALLED post_deliver_barrels()")
    print(f"(first) barrels delivered: {barrels_delivered} order_id: {order_id}")

    total_cost = 0
    num_red_ml_delivered = num_green_ml_delivered = num_blue_ml_delivered = num_dark_ml_delivered = 0

    # Update the ml (inventory) after the barrels are delivered.
    for barrel in barrels_delivered:
        if barrel.potion_type == [1, 0, 0, 0]:
            num_red_ml_delivered += barrel.ml_per_barrel * barrel.quantity
            total_cost += barrel.price * barrel.quantity
        elif barrel.potion_type == [0, 1, 0, 0]:
             num_green_ml_delivered += barrel.ml_per_barrel * barrel.quantity
             total_cost += barrel.price * barrel.quantity
        elif barrel.potion_type == [0, 0, 1, 0]:
             num_blue_ml_delivered += barrel.ml_per_barrel * barrel.quantity
             total_cost += barrel.price * barrel.quantity
        elif barrel.potion_type == [0, 0, 0, 1]:
             num_dark_ml_delivered += barrel.ml_per_barrel * barrel.quantity
             total_cost += barrel.price * barrel.quantity
        # print()
        # print(f"Red ml delivered: {num_red_ml_delivered}")
        # print(f"Green ml delivered: {num_green_ml_delivered}")
        # print(f"Blue ml delivered: {num_blue_ml_delivered}")
        # print(f"Dark ml delivered: {num_dark_ml_delivered}")

    print(f"total cost or total gold paid (final): {total_cost}")
    
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO gold_ledger(gold_change)
            VALUES (:total_cost)
            """
        ),
        [{"total_cost": -total_cost}]
    )
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO ml_ledger(red_ml_change, green_ml_change, blue_ml_change, dark_ml_change)
            VALUES (:red_ml, :green_ml, :blue_ml, :dark_ml)
            """
        ),
        [{"red_ml": num_red_ml_delivered, "green_ml": num_green_ml_delivered, "blue_ml": num_blue_ml_delivered, "dark_ml": num_dark_ml_delivered}]
    )

    print(f"(second) barrels delivered: {barrels_delivered} order_id: {order_id}")

    return {"message": "Delivered barrels and added ml to inventory of all potions."}

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ Purchase a new barrel for r,g,b,d if the potion inventory is low. """
    print("CALLED get_wholesale_purchase_plan()")
    print(f"barrel catalog: {wholesale_catalog}")
    print()

    with db.engine.begin() as connection:

        cur_gold = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(gold_change)
            FROM gold_ledger
            """
        )).scalar_one()

        total_ml = connection.execute(sqlalchemy.text(
            """
            SELECT COALESCE(SUM(red_ml_change + green_ml_change + blue_ml_change + dark_ml_change), 0)
            FROM ml_ledger
            """
        )).scalar() or 0

        ml_capacity = connection.execute(sqlalchemy.text("SELECT ml_c from capacities")).scalar() or 0

    if cur_gold < 300: 
        min_gold_reserve = 0 
        gold_spent_threshold = 1
        print(f"ml capacity: {ml_capacity}")
        print(f"total ml from database: {total_ml}")
        ml_room = ml_capacity - total_ml
        print(f"ml room: {ml_room}")
        available_gold = (cur_gold - min_gold_reserve) * gold_spent_threshold
        print(f"cur_gold less than 500: {cur_gold}")
        print(f"available_gold: {available_gold}")
        large_budget = int(available_gold * 0) #to change back to 0.4
        medium_budget = int(available_gold * 0) #to change back to 0.3
        small_budget = int(available_gold * 1) #to change back to 0.3
        tiered_priority = ["SMALL", "MEDIUM", "LARGE"]
    elif cur_gold < 1000:
        min_gold_reserve = 100 
        gold_spent_threshold = 1 
        print(f"ml capacity: {ml_capacity}")
        print(f"total ml from database: {total_ml}")
        ml_room = ml_capacity - total_ml
        print(f"ml room: {ml_room}")
        available_gold = (cur_gold - min_gold_reserve) * gold_spent_threshold
        print(f"cur_gold less than 1000: {cur_gold}")
        print(f"available_gold: {available_gold}")
        large_budget = int(available_gold * 0) #to change back to 0.4
        medium_budget = int(available_gold * 0.6) #to change back to 0.3
        small_budget = int(available_gold * 0.4) #to change back to 0.3
        tiered_priority = ["MEDIUM", "SMALL", "LARGE"]
    elif cur_gold < 2000: 
        min_gold_reserve = 200 # to change back to 600
        gold_spent_threshold = 0.7 #to change back to 0.7
        print(f"ml capacity: {ml_capacity}")
        print(f"total ml from database: {total_ml}")
        ml_room = ml_capacity - total_ml
        print(f"ml room: {ml_room}")
        available_gold = (cur_gold - min_gold_reserve) * gold_spent_threshold
        print(f"cur_gold more than 1000: {cur_gold}")
        print(f"available_gold: {available_gold}")
        large_budget = int(available_gold * 0.4) #to change back to 0.4
        medium_budget = int(available_gold * 0.5) #to change back to 0.3
        small_budget = int(available_gold * 0.1) #to change back to 0.3
        tiered_priority = ["MEDIUM", "LARGE", "SMALL"]
    else:
        min_gold_reserve = 600 # to change back to 600
        gold_spent_threshold = 0.7 #to change back to 0.7
        print(f"ml capacity: {ml_capacity}")
        print(f"total ml from database: {total_ml}")
        ml_room = ml_capacity - total_ml
        print(f"ml room: {ml_room}")
        available_gold = (cur_gold - min_gold_reserve) * gold_spent_threshold
        print(f"cur_gold more than 1000: {cur_gold}")
        print(f"available_gold: {available_gold}")
        large_budget = int(available_gold * 0.6) #to change back to 0.4
        medium_budget = int(available_gold * 0.3) #to change back to 0.3
        small_budget = int(available_gold * 0.1) #to change back to 0.3
        tiered_priority = ["LARGE", "MEDIUM", "SMALL"]
        
    purchase_plan = []

    if ml_room <= 0 or available_gold <= 0:
        return []
    
    print()
    print(f"large_budget: {large_budget}")
    print(f"medium_budget: {medium_budget}")
    print(f"small_budget: {small_budget}")
    #print()

    print(f"available_gold: {available_gold}")
    print()

    # Inventory check to prioritize colors with lowest stock
    with db.engine.begin() as connection:
        color_inventory = connection.execute(
            sqlalchemy.text(
                """
                SELECT 
                    COALESCE(SUM(red_ml_change), 0) AS red_ml,
                    COALESCE(SUM(green_ml_change), 0) AS green_ml,
                    COALESCE(SUM(blue_ml_change), 0) AS blue_ml,
                    COALESCE(SUM(dark_ml_change), 0) AS dark_ml
                FROM ml_ledger
                """
            )
        ).fetchone()
    
    # Create the initial list of colors with their ml values
    color_priority = [
        ("dark", color_inventory.dark_ml),
        ("red", color_inventory.red_ml),
        ("green", color_inventory.green_ml),
        ("blue", color_inventory.blue_ml)
    ]

    # Separate "dark" from other colors
    fixed_color = [color_priority[0]]  # "dark" is fixed at the first position
    other_colors = color_priority[1:]  # Remaining colors

    # Shuffle the remaining colors
    random.shuffle(other_colors)

    # Combine the fixed color ("dark") with the shuffled other colors
    color_priority = fixed_color + other_colors

    colors_purchased = set()
    print(f"color priority sorted: {color_priority}" )

    for tier in tiered_priority:
        for color, current_ml in color_priority:

            # Condition to skip buying for this color if it's greater than 3000
            if current_ml >= 300: # to change back
                continue

            for barrel in wholesale_catalog:
                if color.upper() in barrel.sku and tier in barrel.sku and barrel.quantity > 0 and ml_room > 0:
                    if color in colors_purchased:
                        continue # Skip if color has already been purchased

                    # Choose what budget to use
                    budget = large_budget if tier == "LARGE" else medium_budget if tier == "MEDIUM" else small_budget

                    # Calculate max quantity that can be purchased
                    max_quantity = min(
                        barrel.quantity, # Available stock in catalog
                        budget // barrel.price, # to check how many barrel I can buy with the budget
                        ml_room // barrel.ml_per_barrel # to check how many ml I can fit in the ml room
                    )
                    # print()
                    # print(f"sku: {barrel.sku}")
                    # print(f"max quantity: {max_quantity}")
                    # print(f"barrel.quantity: {barrel.quantity} ")
                    # print(f"budget: {budget}")
                    # print(f"barrel.price: {barrel.price}")
                    # print(f"ml_room: {ml_room}")
                    # print(f"barrel.ml_per_barrel: {barrel.ml_per_barrel}")
                    # print(f"how many barrels I can buy with my budget - budget // barrel.price: {budget // barrel.price}")
                    # print(f"how many ml I can fit in the ml room - ml_room // barrel.ml_per_barrel: {ml_room // barrel.ml_per_barrel}")
                    
                    if max_quantity > 0:
                        purchase_plan.append(
                            {
                                "sku": barrel.sku,
                                "quantity": max_quantity
                            }
                        )
                        spent = int(max_quantity * barrel.price)
                        budget -= spent
                        ml_room -= max_quantity * barrel.ml_per_barrel
                        barrel.quantity -= max_quantity

                        # print()
                        print(f"spent? {spent}")
                        print(f"budget? {budget}")
                        print(f"ml_room? {ml_room}")
                        print(f"barrel_quantity left in barrel catalog? {barrel.quantity}")
                        print()

                        # Update budget for the current tier
                        if tier == "LARGE":
                            large_budget = budget
                        elif tier == "MEDIUM":
                            medium_budget = budget
                        else:
                            small_budget = budget

                        # print()
                        # print(f"large_budget: {large_budget}")
                        # print(f"medium_budget: {medium_budget}")
                        # print(f"small_budget: {small_budget}")
                        # print()

                        # Mark color as purchased
                        colors_purchased.add(color)

                        # Stop searching for this color in smaller tiers
                        break

        # Rollover unused budget to the next tier
        if tier == "LARGE" and large_budget > 0:
            medium_budget += large_budget
            large_budget = 0
        elif tier == "MEDIUM" and medium_budget > 0:
            small_budget += medium_budget
            medium_budget = 0
    
    print()                
    print(f"let's see my purchase plan: {purchase_plan}")
    return purchase_plan if purchase_plan else [] # Return an empty plan if purchase is not needed

