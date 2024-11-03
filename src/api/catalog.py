import sqlalchemy
from fastapi import APIRouter
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    my_catalog = []

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(potion_ledger.potion_change) AS inventory, sku, price, potion_type
            FROM potions_inventory
            JOIN potion_ledger ON potion_ledger.potion_id = potions_inventory.potion_id
            GROUP BY potions_inventory.potion_id
            """
        ))

    for row in result:
        if (row.inventory > 0):
            my_catalog.append(
                {
                    "sku": row.sku,
                    "name":row.sku,
                    "quantity": row.inventory,
                    "price": row.price,
                    "potion_type": row.potion_type
                }
        )

    print(f"my catalog: {my_catalog}")
    # Return an empty catalog if no potions are available
    return my_catalog 
