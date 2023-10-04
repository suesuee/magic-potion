from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    """ """
    ## Start new implimentation
    for indiv_barrel in barrels_delivered:
        ml_total_delivered=0
        cost_total=0
        current_gold=0
        current_red_ml=0
        if(indiv_barrel.potion_type == [1,0,0,0]):
            ml_total_delivered = indiv_barrel.quantity*indiv_barrel.ml_per_barrel
            cost_total = indiv_barrel.quantity*indiv_barrel.price
        with db.engine.begin() as connection:
            result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
            for row in result:
                current_red_ml = row[2] + ml_total_delivered
                current_gold = row[3] - cost_total
            print(f"Delivery taken of {ml_total_delivered}mL of red potion, at cost of {cost_total}.")
            print(f"Current red potion stock is {current_red_ml}mL, current gold is {current_gold}")
            
            result = connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_red_ml = {current_red_ml}"))
            result = connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = {current_gold}"))

    ## end new implimentation 
    print(barrels_delivered)

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
   
    # Start new implimentation
    purchase_plan = []
    # add entries as more barrels are desired
    purchasing_dict = {
        "SMALL_RED_BARREL": "red",
        "SMALL_GREEN_BARREL": "green",
        "SMALL_BLUE_BARREL": "blue"
    }
    SKIP_COLOR_KEY = "SKIP"
    for for_sale in wholesale_catalog:  # go through catalog
        print("Going through catalog...")
        color = purchasing_dict.get(for_sale.sku, SKIP_COLOR_KEY)
        if color == SKIP_COLOR_KEY:
            # skip if not small barrel
            break
        print(f"Checking {for_sale.sku}...")

        # check current inventory
        with db.engine.begin() as connection:
            result_gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory"))
            result_potion = connection.execute(sqlalchemy.text(f"SELECT num_{color}_potions FROM global_inventory"))
        
        for row in result_gold:
            current_gold = row[0]
        for row in result_potion:
            current_potion = row[0]
        
        # buy 1/3 of possible barrels
        max_barrel = min((current_gold // for_sale.price) // 3, for_sale.quantity)
        
        # only buy if stock is below 10
        if current_potion < 10:
            print(f"Purchacing {max_barrel} small {color} barrels...")
            purchase_plan += [
                {
                    "sku": f"{for_sale.sku}",
                    "quantity": max_barrel,
                }
            ]
        else:
            continue
    
    return purchase_plan