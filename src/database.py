import os
import dotenv
import sqlalchemy
from sqlalchemy import create_engine

def database_connection_url():
    dotenv.load_dotenv()

    return os.environ.get("POSTGRES_URI")

engine = create_engine(database_connection_url(), pool_pre_ping=True)
metadata_obj = sqlalchemy.MetaData()
customers = sqlalchemy.Table("customers", metadata_obj, autoload_with=engine)
potions_inventory = sqlalchemy.Table("potions_inventory", metadata_obj, autoload_with=engine)
carts = sqlalchemy.Table("carts", metadata_obj, autoload_with=engine)
cart_items = sqlalchemy.Table("cart_items", metadata_obj, autoload_with=engine)