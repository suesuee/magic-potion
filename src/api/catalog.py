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
            SELECT SUM(potion_ledger.potion_change) AS inventory, 
                   potions_inventory.sku, 
                   potions_inventory.price, 
                   potions_inventory.potion_type, 
                   potions_inventory.potion_name,
                   ABS(SUM(CASE WHEN potion_ledger.potion_change < 0 THEN potion_ledger.potion_change ELSE 0 END)) AS total_outgoing
            FROM potions_inventory
            JOIN potion_ledger ON potion_ledger.potion_id = potions_inventory.potion_id
            GROUP BY potions_inventory.potion_id, potions_inventory.sku, potions_inventory.price, 
                     potions_inventory.potion_type, potions_inventory.potion_name
            HAVING SUM(potion_ledger.potion_change) > 0
            ORDER BY total_outgoing DESC
            """
        )).fetchall()

    count = 0
    if len(result) > 0:
        for row in result:
            # print(row) - gonna print all the available potions (7)
            if count == 6:
                break
            my_catalog.append(
                {
                    "sku": row.sku,
                    "name":row.potion_name,
                    "quantity": row.inventory,
                    "price": row.price,
                    "potion_type": row.potion_type
                })
            count += 1

    print(f"my catalog: {my_catalog}")
    # Return an empty catalog if no potions are available
    return my_catalog 
