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

        connection.execute(sqlalchemy.text(
            """
            TURNCATE TABLE ml_ledger
            """
        ))    

        connection.execute(sqlalchemy.text(
            """
            TURNCATE TABLE potion_ledger
            """
        ))

        connection.execute(sqlalchemy.text(
            """
            TURNCATE TABLE gold_ledger
            """
        ))
        
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO gold_ledger(gold_change)
            VALUES(100)
            """
        ))

        connection.execute(sqlalchemy.text(
            """
            TURNCATE TABLE cart_items
            """
        ))

        connection.execute(sqlalchemy.text(
            """
            TURNCATE TABLE carts
            """
        ))

    return {"message": "Shop has been reset to 0 for inventory and 100 for gold."}

