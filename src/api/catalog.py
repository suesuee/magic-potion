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
        result = connection.execute(sqlalchemy.text("SELECT * FROM potions_inventory"))

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
