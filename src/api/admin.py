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
        
        # Initialize gold to 100 in the ledger
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO gold_ledger(gold_change)
            VALUES (100)
            """
        ))

        # Clear carts and cart_items
        connection.execute(sqlalchemy.text("TRUNCATE TABLE carts CASCADE"))


    return {"message": "Shop has been reset to 0 for inventory and 100 for gold."}

