import sqlalchemy
from fastapi import APIRouter
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            "SELECT num_red_potions, num_green_potions, num_blue_potions, num_dark_potions FROM global_inventory"
        ))

        row = result.fetchone()

        if row:
            # Fetching data for one row as we only have one row in global_inventory
            cur_red_potions = row[0]
            cur_green_potions = row[1]
            cur_blue_potions = row[2]
            cur_dark_potions = row[3]

    my_catalog = []

    # Offer up for sale in the catalog only the amount of [color] potions that actually exist currently in the inventory!
    if cur_red_potions > 0:
        my_catalog.append({
                    "sku": "RED_POTION_0",
                    "name": "red potion",
                    "quantity": cur_red_potions,
                    "price": 50,
                    "potion_type": [100, 0, 0, 0],           
        })
    if cur_green_potions > 0:
        my_catalog.append({
                    "sku": "GREEN_POTION_0",
                    "name": "green potion",
                    "quantity": cur_green_potions,
                    "price": 50,
                    "potion_type": [0, 100, 0, 0],           
        })
    if cur_green_potions > 0:
        my_catalog.append({
                    "sku": "BLUE_POTION_0",
                    "name": "blue potion",
                    "quantity": cur_blue_potions,
                    "price": 50,
                    "potion_type": [0, 0, 100, 0],           
        })
    if cur_green_potions > 0:
        my_catalog.append({
                    "sku": "DARK_POTION_0",
                    "name": "dark potion",
                    "quantity": cur_dark_potions,
                    "price": 50,
                    "potion_type": [0, 0, 0, 100],           
        })
        
    # Return an empty catalog if no potions are available
    return my_catalog if my_catalog else []
