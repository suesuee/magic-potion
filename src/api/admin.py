import sqlalchemy
from src import database as db
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:

       # Clear all ledger tables
        connection.execute(sqlalchemy.text("TRUNCATE TABLE ml_ledger"))
        connection.execute(sqlalchemy.text("TRUNCATE TABLE potion_ledger"))
        connection.execute(sqlalchemy.text("TRUNCATE TABLE gold_ledger"))
        connection.execute(sqlalchemy.text("TRUNCATE TABLE capacities"))
        connection.execute(sqlalchemy.text("TRUNCATE TABLE ml_c_ledger"))
        connection.execute(sqlalchemy.text("TRUNCATE TABLE potion_c_ledger"))
        
        # Initialize ml in the ledger
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO ml_ledger(red_ml_change, green_ml_change, blue_ml_change, dark_ml_change)
            VALUES (0,0,0,0)
            """
        ))

        # Initialize potion in the ledger
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO potion_ledger(potion_id, potion_change)
            SELECT potions_inventory.potion_id, 0
            FROM potions_inventory
            GROUP BY potions_inventory.potion_id
            """
        ))

        # Initialize gold to 100 in the ledger
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO gold_ledger(gold_change)
            VALUES (100)
            """
        ))

        # Initialize capacities in the ledger
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO capacities(potion_c, ml_c, buy_potion_c, buy_ml_c)
            VALUES (50, 10000, TRUE, TRUE)
            """
        ))

        # # Initialize ml capacities in the ledger
        # connection.execute(sqlalchemy.text(
        #     """
        #     INSERT INTO ml_c_ledger(ml_c_change)
        #     VALUES (10000)
        #     """
        # ))

        # # Initialize potion capacities in the ledger
        # connection.execute(sqlalchemy.text(
        #     """
        #     INSERT INTO potion_c_ledger(potion_c_change)
        #     VALUES (50)
        #     """
        # ))
        

        # Clear carts and cart_items
        connection.execute(sqlalchemy.text("TRUNCATE TABLE carts CASCADE"))


    return {"message": "Shop has been reset to 0 for inventory and 100 for gold."}

