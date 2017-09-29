import pymongo
import json
import os

with open('products.json') as df:
    data = json.load(df)
    