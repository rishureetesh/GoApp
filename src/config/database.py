import os
import sys
import traceback
import urllib

from pymongo.mongo_client import MongoClient
from bson import json_util
from pymongo.server_api import ServerApi

from src.models.db_models import CollectionName


def getMongoClient():
    username = urllib.parse.quote_plus(f"{os.getenv('MONGO_DB_USER')}")
    password = urllib.parse.quote_plus(f"{os.getenv('MONGO_DB_PASSWORD')}")
    host = os.getenv("MONGO_HOST_NAME")
    db = os.getenv("MONGO_DB_NAME")

    uri = f"mongodb+srv://{username}:{password}@{host}/?retryWrites=true&w=majority"

    # client = MongoClient(uri, server_api=ServerApi("1"))
    client = MongoClient("localhost", 27017)
    try:
        client.admin.command("ping")
        cursor = client["GoApp"]
        print(cursor, flush=True)
        return cursor
    except Exception as e:
        print(e)
        return None


# Single point of contact(DataReader)
def SingleDataReader(collection_name, data, requiredFields=None):
    try:
        cursor = getMongoClient()
        collection = cursor[collection_name]
        if requiredFields is None:
            documents = collection.find_one(data)
        else:
            documents = collection.find_one(data, requiredFields)
        return documents
    except Exception as ex:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", ex)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()
        print("DataReader Exception: ", str(ex))


# Single point of contact(Multi data Reader)
def MultiDataReader(collection_name: str, data, requiredFields=None):
    try:
        cursor = getMongoClient()
        collection = cursor[collection_name]
        if requiredFields is None:
            documents = collection.find(data)
        else:
            documents = collection.find(data, requiredFields)
        return documents
    except Exception as ex:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", ex)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()
        print("MultiDataReader Exception: ", str(ex))


# Single point of contact(DataWriter)
def DataWriter(collection_name: str, data, insertMany: bool = False, requiredFields=None):
    try:
        cursor = getMongoClient()
        collection = cursor[collection_name]
        if not insertMany:
            documents = collection.insert_one(data)
        else:
            documents = collection.insert_many(data)
        return documents
    except Exception as ex:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", ex)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()
        print("DataWriter Exception: ", str(ex))


# Single point of contact(DataWriter)
def UpdateWriter(collection_name: str, data, requiredFields=None):
    try:
        cursor = getMongoClient()
        collection = cursor[collection_name]
        documents = collection.update_one(filter=data, update={"$set": requiredFields})
        return documents
    except Exception as ex:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", ex)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()
        print("UpdateWriter Exception: ", str(ex))


# Single point of contact(DataWriter)
def DataAggregation(collection_name: str, aggregation, requiredFields=None):
    try:
        cursor = getMongoClient()
        collection = cursor[collection_name]
        if requiredFields is None:
            documents = list(collection.aggregate(aggregation))
            # documents = [json_util.loads(json_util.dumps(doc)) for doc in documents]
            documents = [{item: data[item] for item in data if item != "_id"} for data in documents]
        else:
            documents = collection.find(aggregation, {"$project": requiredFields})
        return documents
    except Exception as ex:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", ex)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()
        print("DataAggregation Exception: ", str(ex))


# Single point of contact(Delete)
def DeleteData(collection_name: str, data, multi: bool = False):
    try:
        cursor = getMongoClient()
        collection = cursor[collection_name]
        if not multi:
            collection.delete_one(data)
        else:
            collection.delete_many(data)
    except Exception as ex:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", ex)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()
        print("UpdateWriter Exception: ", str(ex))


# Single point of contact(Count)
def CountDocuments(collection_name: str):
    try:
        cursor = getMongoClient()
        collection = cursor[collection_name]
        return collection.count_documents({})
    except Exception as ex:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", ex)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()
        print("UpdateWriter Exception: ", str(ex))


CollectionList = CollectionName()
