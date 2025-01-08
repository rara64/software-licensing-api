from flask_restful import Resource, request
from modules.limiter import limiter
from modules.authentication import admin_only, is_admin, authenticated
from config import config
from flask import jsonify
from bson.objectid import ObjectId
from modules.license_generator import get_license
from datetime import datetime, timezone
from modules.validator import is_valid_objectid
import json

def get_license_details(requested_license_detail, db_client, license_id, user_id, is_admin=False):
    
    licenses_collection = None

    match requested_license_detail:
        case "binded_hardware_id":
            licenses_collection = db_client[config.LICENSES_COLLECTION].find_one(
                {"license_id": ObjectId(license_id)} if is_admin else {"license_id": ObjectId(license_id), "user_id": user_id},
                {"binded_hardware_id": 1, "_id": 0})
        case "license_key":
            licenses_collection = db_client[config.LICENSES_COLLECTION].find_one(
                {"license_id": ObjectId(license_id)} if is_admin else {"license_id": ObjectId(license_id), "user_id": user_id},
                {"license_key": 1, "_id": 0})
        case "issued_at":
              licenses_collection = db_client[config.LICENSES_COLLECTION].find_one(
                {"license_id": ObjectId(license_id)} if is_admin else {"license_id": ObjectId(license_id), "user_id": user_id},
                {"issued_at": 1, "_id": 0})
        case "last_activated_at":
            licenses_collection = db_client[config.LICENSES_COLLECTION].find_one(
                {"license_id": ObjectId(license_id)} if is_admin else {"license_id": ObjectId(license_id), "user_id": user_id},
                {"last_activated_at": 1, "_id": 0})
        case "user_id":
            licenses_collection = db_client[config.LICENSES_COLLECTION].find_one(
                {"license_id": ObjectId(license_id)} if is_admin else {"license_id": ObjectId(license_id), "user_id": user_id},
                {"user_id": 1, "_id": 0})

    return licenses_collection

class licenses(Resource):
    def __init__(self, db_client):
        self.db_client = db_client
    
    """
    /licenses GET [ADMIN ONLY]

    /licenses?user_id= GET 
    /licenses?user_id=me GET

    /licenses/<license_id> GET

    /licenses/<license_id>/binded_hardware_id GET
    /licenses/<license_id>/license_key GET
    /licenses/<license_id>/user_id GET
    /licenses/<license_id>/issued_at GET
    /licenses/<license_id>/last_activated_at GET

    Retrieve information about licenses
    When authenticated as a normal user, you get access to licenses assigned to your account
    """
    @limiter.exempt
    @authenticated
    @is_admin
    def get(self, user_id="", is_admin=False, license_id="", requested_license_detail=""):
        licenses_collection = None
        query_user_id = request.args["user_id"]

        # ?user_id=me macro
        if query_user_id == "me":
            query_user_id = user_id
        
        if license_id != "" and not is_valid_objectid(license_id):
            return {'message': 'License not found.'}, 404 

        # /licenses/<license_id>
        if license_id != "" and requested_license_detail == "":

            licenses_collection = self.db_client[config.LICENSES_COLLECTION].find_one(
                    {"license_id": ObjectId(license_id)} if is_admin else {"user_id": user_id, "license_id": ObjectId(license_id)},
                    {"_id": 0})
            
            if not licenses_collection:
                return {'message': 'License not found.'}, 404 
            else:
                return json.loads(json.dumps(licenses_collection, default=str))
        
        # /licenses
        # /licenses?user_id=
        elif license_id == "" and requested_license_detail == "":

            # /licenses?user_id=
            if query_user_id and is_valid_objectid(query_user_id):
                licenses_collection = self.db_client[config.LICENSES_COLLECTION].find({"user_id": (query_user_id if is_admin else user_id)})
            elif query_user_id:
                return jsonify(list())

            # /licenses
            elif len(request.args.listvalues()) == 0:
                # /licenses for ADMIN
                if is_admin:
                    licenses_collection = self.db_client[config.LICENSES_COLLECTION].find({})
                # /licenses for normal USER
                else:
                    return {'message': 'Endpoint access unauthorized. You can try accessing it with `?user_id=me`.'}, 401

            # /licenses with any other ? query
            else:
                return {'message': 'Unsupported query in URL.'}, 400

        
        # /licenses/<license_id>/binded_hardware_id
        # /licenses/<license_id>/license_key
        # /licenses/<license_id>/user_id
        # /licenses/<license_id>/issued_at
        # /licenses/<license_id>/activated_at
        elif license_id != "" and requested_license_detail != "":

            if requested_license_detail not in ["binded_hardware_id", "license_key", "user_id", "issued_at", "last_activated_at"]:
                return {'message': "Requested license detail doesn't exist."}, 404
            
            # /licenses/<license_id>/<requested_license_detail>
            licenses_collection = get_license_details(requested_license_detail=requested_license_detail, db_client=self.db_client, license_id=license_id, user_id=user_id, is_admin=is_admin)

            if not licenses_collection:
                return {'message': 'License not found.'}, 404 
            else:
                return json.loads(json.dumps(licenses_collection, default=str))

        return json.loads(json.dumps(list(licenses_collection), default=str))

    """
    [ADMIN ONLY]
    /license POST
    Generate a new license key assigned to a specific user_id

    {
        "user_id": ""
    }
    """
    @limiter.exempt
    @admin_only
    def post(self, user_id="", license_key="", requested_license_detail=""):
        if requested_license_detail != "":
            return {'message': 'Unsupported operation.'}, 400

        data = request.get_json()
        user_id = data.get("user_id")

        if user_id and is_valid_objectid(user_id):
            user = self.db_client[config.USERS_COLLECTION].find_one({"_id": ObjectId(user_id)})
            if user:
                license_key = get_license()
                self.db_client[config.LICENSES_COLLECTION].insert_one({"license_key": license_key, "user_id": user_id, "issued_at": datetime.now(timezone.utc), "binded_hardware_id": "", "last_activated_at": ""})
                return {'message': 'License was successfully generated.', 'data': license_key}, 201

        return {'message': 'License not found.'}, 404 
    
    """
    [ADMIN ONLY]
    /licenses/<license_id> DELETE
    Remove a license key
    """
    @limiter.exempt
    @admin_only
    def delete(self, user_id="", license_id="", requested_license_detail=""):
        if requested_license_detail != "":
            return {'message': 'Unsupported operation.'}, 400

        if not is_valid_objectid(license_id):
            return {'message': 'License not found.'}, 404 

        key = self.db_client[config.LICENSES_COLLECTION].find_one({"_id": ObjectId(license_id)})
        if key:
            self.db_client[config.LICENSES_COLLECTION].delete_one({"_id": ObjectId(license_id)})
            return {'message': 'License was successfully deleted.'}, 200
        
        return {'message': 'License not found.'}, 404    


    """
    [ADMIN ONLY]
    /licenses/<license_id> PATCH
    Update user_id or binded_hardware_id assigned to the license key
    
    {
        "user_id": ""
    }

    {
        "binded_hardware_id:""
    }
    """
    @limiter.exempt
    @admin_only
    def patch(self, user_id="", license_id="", requested_license_detail=""):
        if not is_valid_objectid(license_id):
            return {'message': 'License not found.'}, 404
        
        if requested_license_detail != "":
            return {'message': 'Unsupported operation.'}, 400

        data = request.get_json()
        user_id = data.get("user_id")
        binded_hardware_id = data.get("binded_hardware_id")

        license = self.db_client[config.LICENSES_COLLECTION].find_one({"_id": ObjectId(license_id)})
        if license:
            new_data = {}

            if user_id:
                new_data["user_id"] = user_id
            
            if binded_hardware_id:
                new_data["binded_hardware_id"] = binded_hardware_id

            if new_data != {}:
                self.db_client[config.LICENSES_COLLECTION].update_one({"_id": ObjectId(license_id)}, {"$set": new_data}, True)
                return {'message': 'License was successfully updated.'}, 200
            else:
                return {'message': 'No new data specified in request body.'}, 400

        return {'message': 'License not found.'}, 404
    
    @limiter.exempt
    @admin_only
    def put(self, user_id="", license_key="", requested_license_detail=""):
        return {'message': 'PUT requests are not supported for licenses. Use PATCH to update license details.'}, 400