from flask_restful import Resource, request
from modules.authentication import is_admin, authenticated, admin_only
from modules.validator import is_valid_objectid
from config import config
from bson import ObjectId
import json

def get_checksum_details(checksum_id, requested_checksum_detail, db_client):
    checksums_collection = None

    match requested_checksum_detail:
        case "checksum":
            checksums_collection = db_client[config.CHECKSUMS_COLLECTION].find_one({"_id": ObjectId(checksum_id)}, {"checksum": 1, "_id": 0})
        case "software_version":
            checksums_collection = db_client[config.CHECKSUMS_COLLECTION].find_one({"_id": ObjectId(checksum_id)}, {"software_version": 1, "_id": 0})

    return checksums_collection


class checksums(Resource):
    def __init__(self, db_client):
        self.db_client = db_client

    """

    /checksums GET
    /checksums?software_version= GET
    /checksums?checksum= GET

    /checksums/<checksum_id> GET
    /checksums/<checksum_id>/<requested_checksum_detail> GET

    Retrieve checksums for specific software versions
    Available to all authenticated users

    """
    @authenticated
    def get(self, user_id="", checksum_id="", requested_checksum_detail=""):
        checksums_collection = None

        if not is_valid_objectid(checksum_id) and checksum_id != "":
            return {'message': 'Checksum not found.'}, 404
        
        if checksum_id == "" and requested_checksum_detail == "":

            # /checksums?software_version=
            if ("software_version" in request.args.keys()):
                checksums_collection = self.db_client[config.CHECKSUMS_COLLECTION].find_one({"software_version": request.args["software_version"]})

            # /checksums?checksum=
            elif ("checksum" in request.args.keys()):
                checksums_collection = self.db_client[config.CHECKSUMS_COLLECTION].find_one({"checksum": request.args["checksum"]})
            
            elif len(request.args.keys()) != 0:
                return {'message': 'Unsupported query in URL.'}, 400
            
            # /checksums
            else:
                checksums_collection = self.db_client[config.CHECKSUMS_COLLECTION].find({})
                return json.loads(json.dumps(list(checksums_collection), default=str))
        
        # /checksums/<checksum_id>
        elif checksum_id != "" and requested_checksum_detail == "":
            checksums_collection = self.db_client[config.CHECKSUMS_COLLECTION].find_one({"_id": ObjectId(checksum_id)})

        # /checksums/<checksum_id>/<requested_checksum_detail>
        elif checksum_id != "" and requested_checksum_detail != "":
            if requested_checksum_detail in ["checksum", "software_version"]:
                checksums_collection = get_checksum_details(checksum_id, requested_checksum_detail, self.db_client)
            else:
                return {'message': "Requested checksum detail doesn't exist."}, 400

        if not checksums_collection:
            return {'message': 'Checksum not found.'}, 404
        
        return json.loads(json.dumps(checksums_collection, default=str))
    
    """
    /checksums POST [ADMIN ONLY]

    {
        "checksum": "",
        "software_version": ""
    }

    Add new checksum entry for a software version
    """

    @admin_only
    def post(self, user_id="", checksum_id="", requested_checksum_detail=""):
        if requested_checksum_detail != "" or checksum_id != "":
            return {'message': 'Unsupported opperation.'}, 400
        
        data = request.get_json()
        new_checksum = data.get("checksum")
        software_version = data.get("software_version")

        if new_checksum and software_version:
            checksum = self.db_client[config.CHECKSUMS_COLLECTION].find_one({"software_version": software_version})
            if checksum:
                return {'message': 'Checksum for that software version already exists.'}, 409
        
            self.db_client[config.CHECKSUMS_COLLECTION].insert_one({"checksum": new_checksum, "software_version": software_version})
        else:
            return {'message': 'Not all details were provided for the new checksum (checksum, software_version).'}, 400
        
        return {'message': 'Checksum entry was successfully created.'}, 201
        
    """

    /checksums/<checksum_id> DELETE [ADMIN ONLY]
    Delete specific checksum entry

    """

    @admin_only
    def delete(self, user_id="", checksum_id="", requested_checksum_detail=""):
        if requested_checksum_detail != "":
            return {'message': 'Unsupported opperation.'}, 400    
        
        if not is_valid_objectid(checksum_id):
            return {'message': 'Checksum ID not found.'}, 404
        
        checksum = self.db_client[config.CHECKSUMS_COLLECTION].find_one({"_id": ObjectId(checksum_id)})
        if checksum:
            self.db_client[config.CHECKSUMS_COLLECTION].delete_one({"_id": ObjectId(checksum_id)})
            return {'message': 'Checksum entry was successfully deleted.'}, 200
        
        return {'message': 'Checksum ID not found.'}, 404    
    
    """

    /checksums PATCH [ADMIN ONLY]
    Update checksum entry

    {
        "checksum": ""
    }

    {
        "software_version": ""
    }

    """

    @admin_only
    def patch(self, user_id="", checksum_id="", requested_checksum_detail=""):
        if requested_checksum_detail != "":
            return {'message': 'Unsupported opperation.'}, 400    
        
        if not is_valid_objectid(checksum_id):
            return {'message': 'Checksum ID not found.'}, 404
        
        data = request.get_json()
        new_checksum = data.get("checksum")
        new_software_version = data.get("software_version")

        checksum = self.db_client[config.CHECKSUMS_COLLECTION].find_one({"_id": ObjectId(checksum_id)})
        if checksum:
            new_data = {}

            if new_checksum:
                new_data["checksum"] = new_checksum
            
            if new_software_version:
                checksum_check = self.db_client[config.CHECKSUMS_COLLECTION].find_one({"software_version": new_software_version})
                if checksum_check:
                    return {'message': 'Checksum for that software version already exists.'}, 409
            
                new_data["software_version"] = new_software_version

            if new_data != {}:
                self.db_client[config.CHECKSUMS_COLLECTION].update_one({"_id": ObjectId(checksum_id)}, {"$set": new_data}, True)
                return {'message': 'Checksum was successfully updated.'}, 200
            else:
                return {'message': 'No new data specified in request body.'}, 400

        return {'message': 'Checksum ID not found.'}, 404      

    @admin_only
    def put(self, user_id="", checksum_id="", requested_checksum_detail=""):
        return {'message': 'PUT requests are not supported for checksums. Use PATCH to update checksum entry details.'}, 400
        

