from xmlrpc.client import Boolean
import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from src.models.db_schema import CollectionName

def getMongoClient():
    username = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    host = os.getenv("DB_HOST")
    db = os.getenv("DB_NAME")

    uri = f"mongodb://{username}:{password}@{host}/?retryWrites=true&w=majority"
    
    client = MongoClient(uri, server_api=ServerApi("1"))
    try:
        client.admin.command("ping")
        cursor = client[db]
        return cursor
    except Exception as e:
        print(e)
        return None
    

# Single poit of contact(DataReader)
def SingleDataReader(collection_name:str, data, requiredFields=None):
    try:
        cursor = getMongoClient()
        collection = cursor[collection_name]
        if requiredFields is None:
            documents = collection.find_one(data)
        else:
            documents = collection.find_one(data, requiredFields)
        return documents
    except Exception as ex:
        print("SingleDataReader Exception: ", str(ex))


# Single point of contact(DataWriter)
def DataWriter(collection_name:str, data, insertMany:Boolean=False):
    try:
        cursor = getMongoClient()
        collection = cursor[collection_name]
        if not insertMany:
            documents = collection.insert_one(data)
        else:
            documents = collection.insert_many(data)
        return documents
    except Exception as ex:
        print("DataWriter Exception: ", str(ex))

db = getMongoClient()
c_name = CollectionName