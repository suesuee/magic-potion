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
            "SELECT num_green_potions FROM global_inventory WHERE id = 1"
        ))

        row = result.fetchone()

        if row:
        # Fetching data for one row only as of now
            cur_green_potions = row[0]

    # Offer up for sale in the catalog only the amount of green potions that actually exist currently in the inventory!
    if cur_green_potions > 0: 
        return [
                {
                    "sku": "GREEN_POTION_0",
                    "name": "green potion",
                    "quantity": cur_green_potions,
                    "price": 50,
                    "potion_type": [0, 100, 0, 0],
                }
            ]
    else:
        # Return an empty catalog if no potions are available
        return []
