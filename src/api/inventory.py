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
        row = connection.execute(sqlalchemy.text(
            """
            SELECT 
            (SELECT COALESCE(SUM(red_ml_change), 0) FROM ml_ledger) AS red_ml,
            (SELECT COALESCE(SUM(green_ml_change), 0) FROM ml_ledger) AS green_ml,
            (SELECT COALESCE(SUM(blue_ml_change), 0) FROM ml_ledger) AS blue_ml,
            (SELECT COALESCE(SUM(dark_ml_change), 0) FROM ml_ledger) AS dark_ml,
            (SELECT COALESCE(SUM(gold_change), 0) FROM gold_ledger) AS gold
            """
        )).fetchone()
        total_ml = row.red_ml + row.green_ml + row.blue_ml + row.dark_ml
        gold = row.gold

        total_potions = connection.execute(sqlalchemy.text(
            """
            SELECT COALESCE(SUM(potion_change), 0) FROM potion_ledger
            """
        )).scalar_one() or 0

    return {
        "number_of_potions": total_potions,
        "ml_in_barrels": total_ml,
        "gold": gold
    }

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """
    print("CALLED get_capacity_plan().")
    with db.engine.begin() as connection:
        inventory_row = connection.execute(sqlalchemy.text(
            """
            SELECT 
                (SELECT COALESCE(SUM(gold_change), 0) FROM gold_ledger) AS gold, 
                (SELECT COALESCE(SUM(red_ml_change) + SUM(green_ml_change) + SUM(blue_ml_change) + SUM(dark_ml_change), 0) FROM ml_ledger) AS total_ml,
                (SELECT COALESCE(SUM(potion_change), 0) FROM potion_ledger) AS total_potions
            """
        )).fetchone()
    
        gold = inventory_row.gold
        total_ml = inventory_row.total_ml
        total_potions = inventory_row.total_potions
    
    with db.engine.begin() as connection:
        capacity_row = connection.execute(sqlalchemy.text(
            """
            SELECT potion_c, ml_c, buy_potion_c, buy_ml_c
            FROM capacities
            """
        )).fetchone()

        potion_capacity = capacity_row.potion_c
        ml_capacity = capacity_row.ml_c
        buy_potion = capacity_row.buy_potion_c
        buy_ml = capacity_row.buy_ml_c
    
    gold_to_buy_capacity_threshold = 1 #to change back to 0.5
    # use the threshold I set of my available gold to buy capacities
    #gold_to_buy_capacity = max(gold // 4, 0) if gold >= 4000 else 0
    gold_to_buy_capacity = (gold * gold_to_buy_capacity_threshold)
    print(f"gold_to_buy_capacity (1): {gold_to_buy_capacity}")

    potion_capacity_to_buy = 0
    ml_capacity_to_buy = 0
    capacity_threshold = 0.6 #to change back
    print()
    print(f"total potion: {total_potions}")
    print(f"potion capacity: {potion_capacity}")
    print(f"75% of potion_capacity: {potion_capacity * capacity_threshold}")
    print()
    print(f"total ml: {total_ml}")
    print(f"ml capacity: {ml_capacity}")
    print(f"75% of ml_capacity: {ml_capacity * capacity_threshold}")
    print()

    if (
        gold_to_buy_capacity >= 1000
        and total_potions > (potion_capacity * capacity_threshold)
        and buy_potion
    ):
        potion_capacity_to_buy = 1
        gold_to_buy_capacity -= 1000
    
    print(f"gold_to_buy_capacity for potion: {gold_to_buy_capacity}")

    # how many capacity I have in my database
    num_potion_capacity = potion_capacity // 50
    num_ml_capacity = ml_capacity // 10000
    print(f"num_potion_capacity: {num_potion_capacity}")
    print(f"num_ml_capacity: {num_ml_capacity}")
    print()

    if (
        gold_to_buy_capacity >= 1000
        and total_ml > (ml_capacity * capacity_threshold)
        and buy_ml
        and num_ml_capacity <= num_potion_capacity
    ):
        ml_capacity_to_buy = 1
        gold_to_buy_capacity -= 1000

    print(f"gold_to_buy_capacity for ml: {gold_to_buy_capacity}")
    
    # use this later in the game
    # if (
    #     gold_to_buy_capacity >= 1000
    #     and total_ml > (ml_capacity * capacity_threshold)
    #     and buy_ml
    #     and potion_capacity_to_buy == 0
    #     and num_ml_capacity <= num_potion_capacity
    # ):
    #     ml_capacity_to_buy = 1
    #     gold_to_buy_capacity -= 1000
    print()
    print(f"potion_capacity: {potion_capacity_to_buy}")
    print(f"ml_capacity: {ml_capacity_to_buy}")
        
    return {
        "potion_capacity": potion_capacity_to_buy,
        "ml_capacity": ml_capacity_to_buy
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
    print("CALLED deliver_capacity_plan().")
    potion_to_add = capacity_purchase.potion_capacity * 50
    ml_to_add = capacity_purchase.ml_capacity * 10000
    gold_paid = (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000

    # Update capacities 
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            """
            UPDATE capacities 
            SET potion_c = potion_c + :potion_to_add,
                ml_c = ml_c + :ml_to_add
            """
        ),{
            "potion_to_add": potion_to_add,
            "ml_to_add": ml_to_add
        })

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO gold_ledger(gold_change)
            VALUES (:gold_change)
            """
        ), {"gold_change": -gold_paid})
    
    if ml_to_add > 0:
        with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text(
                """
                INSERT INTO ml_c_ledger(ml_c_change)
                VALUES (:ml_c_change)
                """
            ), {"ml_c_change": ml_to_add})
    
    if potion_to_add > 0:
        with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text(
                """
                INSERT INTO potion_c_ledger(potion_c_change)
                VALUES (:potion_c_change)
                """
            ), {"potion_c_change": potion_to_add})
    
    print(f"Potion Capacity increase: {potion_to_add} and ML Capacity increase: {ml_to_add}~")
    return "OK"
        

    
