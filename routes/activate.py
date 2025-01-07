from flask_restful import Resource, request
from modules.limiter import limiter
from modules.authentication import authenticated
from config import config
from bson.objectid import ObjectId
from modules.license_generator import get_hardware_id, get_signed_license
from datetime import datetime, timezone

class activate(Resource):
    def __init__(self, db_client):
        self.db_client = db_client

    """
    Get a license signed by the API private key
    /activate POST

    {
        "hardware_spec1":""
        "hardware_spec2":""
        "hardware_spec3":""
        "hardware_spec4":""
        "hardware_spec5":""
        "license_key":""
    }
    """
    @limiter.exempt
    @authenticated
    def post(self, user_id=""):
        data = request.get_json()
        hardware_spec1 = data.get("hardware_spec1")
        hardware_spec2 = data.get("hardware_spec2")
        hardware_spec3 = data.get("hardware_spec3")
        hardware_spec4 = data.get("hardware_spec4")
        hardware_spec5 = data.get("hardware_spec5")
        license_key = data.get("license_key")
        if license_key:
            license = self.db_client[config.LICENSES_COLLECTION].find_one({"license_key": license_key})
            if license:
                if license.get("user_id") == user_id:
                    if license.get("binded_hardware_id") == "":

                        hardware_id = get_hardware_id(hardware_spec1, hardware_spec2, hardware_spec3, hardware_spec4, hardware_spec5)
                        signed_license = get_signed_license(license_key, hardware_id)
                        self.db_client[config.LICENSES_COLLECTION].update_one({"_id": ObjectId(license.get("_id"))}, {"$set": {"binded_hardware_id": hardware_id, "last_activated_at": datetime.now(timezone.utc)}}, True)

                        return {"message":"License was successfully binded and activated.", "data": signed_license}, 200
                    
                    return {"message": "License was already activated. Activation failed."}, 409
        
        return {"message": "License not found."}, 404
    