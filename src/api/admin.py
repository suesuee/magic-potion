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
        connection.execute(sqlalchemy.text("""
            UPDATE global_inventory 
            SET num_green_ml = 0, 
                num_red_ml = 0, 
                num_blue_ml = 0, 
                num_dark_ml = 0, 
                gold = 100,
            """
            ))
        
        connection.execute(sqlalchemy.text("""
            UPDATE potions_inventory
            SET inventory = 0
        """))

        connection.execute(sqlalchemy.text("""
            DELETE FROM cart_items
        """))

        connection.execute(sqlalchemy.text("""
            DELETE FROM carts
        """))

    return {"message": "Shop has been reset to 0 for inventory and 100 for gold."}

