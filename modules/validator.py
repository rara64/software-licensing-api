from bson import ObjectId
import re

def is_valid_objectid(value):
    try:
        ObjectId(value)
        return True
    except:
        return False
    
def is_valid_email(value):
    return bool(re.match(r"^[a-z0-9]+@[a-z]+\.[a-z]{2,3}$", value))

def is_valid_username(value):
    return bool(re.match(r"^[A-Za-z0-9]+$", value))