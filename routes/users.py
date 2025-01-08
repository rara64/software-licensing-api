from flask_restful import Resource, request
from modules.limiter import limiter
from modules.authentication import authenticated, is_admin, admin_only
from config import config
import bcrypt
from bson.objectid import ObjectId
import json
import pyotp
from modules.validator import is_valid_email, is_valid_username, is_valid_objectid

def get_user_details(requested_user_detail, requested_user_id, db_client, user_id, is_admin=False):
    
    collection = None

    match requested_user_detail:
        case "email":
            collection = db_client[config.USERS_COLLECTION].find_one({"_id": ObjectId(requested_user_id)} if is_admin else {"_id": ObjectId(user_id)}, {"email": 1, "_id": 0})
        case "username":
            collection = db_client[config.USERS_COLLECTION].find_one({"_id": ObjectId(requested_user_id)} if is_admin else {"_id": ObjectId(user_id)}, {"username": 1, "_id": 0})

    return collection

class users(Resource):
    def __init__(self, db_client):
        self.db_client = db_client

    """
    /users GET [ADMIN ONLY]

    /users/me GET
    /users/me/email GET
    /users/me/username GET

    -- LIMITED ACCESS FOR NORMAL USERS --

    /users/<requested_user_id> GET
    /users/<requested_user_id>/email GET
    /users/<requested_user_id>/username GET
    /users/<requested_user_id/licenses GET

    -------------------------------------

    /users?email= GET [ADMIN ONLY]
    /users?username= GET [ADMIN ONLY]

    Get information about users
    When authenticated as a normal user, you can see your current user details
    """

    @authenticated
    @is_admin
    @limiter.exempt
    def get(self, is_admin=False, user_id="", requested_user_id="", requested_user_detail=""):

        users_collection = None

        # /users/me macro
        if requested_user_id == "me":
            requested_user_id = user_id

        if not is_valid_objectid(requested_user_id) and requested_user_id != "":
            return {'message': 'User not found.'}, 404


        # /users endpoints for ADMIN
        if is_admin and requested_user_id != config.ADMIN_ID:
            # /users
            if len(request.args.listvalues()) == 0 and requested_user_id == "" and requested_user_detail == "":
                users_collection = self.db_client[config.USERS_COLLECTION].find({}, {"password": 0})

            # /users?email=
            elif "email" in request.args.keys() and requested_user_id == "" and requested_user_detail == "":
                users_collection = self.db_client[config.USERS_COLLECTION].find({"email": request.args["email"]}, {"password": 0})

            # /users?username=
            elif "username" in request.args.keys() and requested_user_id == "" and requested_user_detail == "":
                users_collection = self.db_client[config.USERS_COLLECTION].find({"username": request.args["username"]}, {"password": 0})

            # /users/<requested_user_id>
            elif requested_user_id != "" and requested_user_detail == "":

                users_collection = self.db_client[config.USERS_COLLECTION].find_one({"_id": ObjectId(requested_user_id)}, {"password": 0})

                if not users_collection:
                    return {'message': 'User not found.'}, 404
                
                licenses_collection = self.db_client[config.LICENSES_COLLECTION].find({"user_id": user_id}, {"user_id": 0})

                users_collection["licenses"] = list(licenses_collection)

            # /users/<requested_user_id>/<requested_user_detail>
            elif requested_user_id != "" and requested_user_detail != "":

                users_collection = self.db_client[config.USERS_COLLECTION].find_one({"_id": ObjectId(requested_user_id)}, {"password": 0})
                
                if not users_collection:
                    return {'message': 'User not found.'}, 404
                
                if requested_user_detail in ["email", "username"]:
                    users_collection = get_user_details(requested_user_detail=requested_user_detail, requested_user_id=requested_user_id, db_client=self.db_client, user_id=user_id, is_admin=is_admin)
                elif requested_user_detail == "licenses":
                    collection = self.db_client[config.LICENSES_COLLECTION].find({"user_id": requested_user_id}, {"user_id": 0})
                    return json.loads(json.dumps(list(collection), default=str))
                else:
                    return {'message': "Requested user detail doesn't exist."}, 404
                
                return json.loads(json.dumps(users_collection, default=str))
            

            return json.loads(json.dumps(list(users_collection), default=str))


        # /users endpoints for normal USER 
        else:
            # /users/<requested_user_id>/<requested_user_detail>
            if requested_user_id != user_id and requested_user_id != "me" and requested_user_id != "":
                return {'message': 'User not found.'}, 404
            
            if requested_user_detail != "":
                if requested_user_detail in ["email", "username"]:
                    users_collection = get_user_details(requested_user_detail=requested_user_detail, requested_user_id=requested_user_id, db_client=self.db_client, user_id=user_id, is_admin=is_admin)
                elif requested_user_detail == "licenses":
                    collection = self.db_client[config.LICENSES_COLLECTION].find({"user_id": user_id}, {"user_id": 0})
                    return json.loads(json.dumps(list(collection), default=str))
                else:
                    return {'message': "Requested user detail doesn't exist."}, 404
            
            # /users/<requested_user_id>
            if requested_user_detail == "" and requested_user_id != "":
                users_collection = self.db_client[config.USERS_COLLECTION].find_one({"_id": ObjectId(user_id)}, {"password":0})

                licenses_collection = self.db_client[config.LICENSES_COLLECTION].find({"user_id": user_id}, {"user_id": 0})

                users_collection["licenses"] = list(licenses_collection)

            # /users
            if requested_user_id == "" and requested_user_detail == "":
                return {'message': 'Endpoint access unauthorized.'}, 401

            return json.loads(json.dumps(users_collection, default=str))

    """
    [ADMIN ONLY]
    /users POST
    Create a new user

    {
        "username": ""
        "password": ""
        "email": ""
    }
    """
    @limiter.exempt
    @admin_only
    def post(self, user_id="", requested_user_id="", requested_user_detail=""):
        if requested_user_id != "" or requested_user_detail != "":
            return {'message': 'Unsupported operation.'}, 400  
        
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")
        mail = data.get("email")

        if username and password and mail:

            if not is_valid_username(username):
                return {'message': 'Username was invalid. Username cannot be empty and should only consist of letters or numbers.'}, 400    
            if not is_valid_email(mail):
                return {'message': 'Email address was invalid.'}, 400

            user = self.db_client[config.USERS_COLLECTION].find_one({"username": username})
            if not user:
                hashed_password = bcrypt.hashpw(bytes(password, 'utf-8'), bcrypt.gensalt())
                self.db_client[config.USERS_COLLECTION].insert_one({"username": username, "password": hashed_password, "email": mail})
                return {'message': 'User was successfully added.'}, 201  
               
            else:
                return {'message': 'User already exists.'}, 409
        
        return {'message': 'Not all details were provided for the new user (username, password, email).'}, 400    

    """
    [ADMIN ONLY]
    /users/<requested_user_id> DELETE
    Delete a user
    """
    @limiter.exempt
    @admin_only
    def delete(self, user_id="", requested_user_id="", requested_user_detail=""):
        if requested_user_detail != "":
            return {'message': 'Unsupported operation.'}, 400  
        
        if not is_valid_objectid(requested_user_id):
            return {'message': 'User not found.'}, 404
        
        if requested_user_id == user_id:
            return {'message': 'You cannot delete yourself.'}, 400
        
        user = self.db_client[config.USERS_COLLECTION].find_one({"_id": ObjectId(requested_user_id)})
        if user:
            self.db_client[config.USERS_COLLECTION].delete_one({"_id": ObjectId(requested_user_id)})
            return {'message': 'User was successfully deleted.'}, 200    
        
        return {'message': 'User not found.'}, 404 

    """
    [ADMIN ONLY]
    /users/<requested_user_id> PATCH
    Update user information

    {
        "email":""
    }
    {
        "password":""
    }
    {
        "username":""
    }

    /users/<requested_user_id> PATCH
    When authenticated as a normal user, you can update your user details

    {
        "email":""
    }
    {
        "password":""
    }
    """
    @limiter.exempt
    @authenticated
    @is_admin
    def patch(self, is_admin=False, user_id="", requested_user_id="", requested_user_detail=""):
        if requested_user_detail != "":
            return {'message': 'Unsupported operation.'}, 400  
        
        if requested_user_id == "me":
            requested_user_id = user_id

        if not is_valid_objectid(requested_user_id):
            return {'message': 'User not found.'}, 404
        
        if requested_user_id != "":
            # /users/<requested_user_id> for ADMIN
            if is_admin:
                user = self.db_client[config.USERS_COLLECTION].find_one({"_id": ObjectId(requested_user_id)})
                if user:

                    if user.get("_id") == config.ADMIN_ID and config.ADMIN_OTP_SECRET.strip() != "":
                        otp = data.get("otp")
                        totp = pyotp.TOTP(config.ADMIN_OTP_SECRET)
                        if str(otp) != str(totp.now()):
                            return {'message': 'Invalid or no `otp` provided for changing admin details.'}, 401
                
                    data = request.get_json()
                    new_email = data.get("email")
                    new_username = data.get("username")
                    new_password = data.get("password")

                    if new_username and not is_valid_username(new_username):
                        return {'message': 'New username was invalid. Username cannot be empty and should only consist of letters or numbers.'}, 400
                    
                    if new_email and not is_valid_email(new_email):
                        return {'message': 'New email address was invalid.'}, 400

                    new_data = {}

                    if new_username:
                        user_found = self.db_client[config.USERS_COLLECTION].find_one({"username": new_username})
                        if user_found:
                            return {'message': 'User with the requested new name already exists.'}, 409
                        else:
                            new_data["username"] = new_username
                    
                    if new_email:
                        new_data["email"] = new_email
                    
                    if new_password:
                        hashed_password = bcrypt.hashpw(bytes(new_password, 'utf-8'), bcrypt.gensalt())
                        new_data["password"] = hashed_password
                    
                    if new_data != {}:
                        self.db_client[config.USERS_COLLECTION].update_one({"_id": ObjectId(requested_user_id)}, {"$set": new_data}, True)
                        return {'message': 'User details were successfully updated.'}, 200
                    else:
                        return {'message': 'No new data specified in request body.'}, 400
                    
                else:
                    return {'message': 'User not found.'}, 404
        
            # /users/<requested_user_id> for normal USER
            else:
                if requested_user_id != user_id:
                    return {'message': 'User not found.'}, 404
                
                data = request.get_json()
                new_email = data.get("email")
                new_password = data.get("password")

                if new_email and not is_valid_email(new_email):
                    return {'message': 'New email address was invalid.'}, 400

                new_data = {}

                if new_email:
                   new_data["email"] = new_email
            
                if new_password:
                    hashed_password = bcrypt.hashpw(bytes(new_password, 'utf-8'), bcrypt.gensalt())
                    new_data["username"] = new_username

                if new_data != {}:
                    self.db_client[config.USERS_COLLECTION].update_one({"_id": ObjectId(user_id)},
                        {"$set": new_data}, True)
                    return {'message': 'User details were successfully updated.'}, 200
                else:
                    return {'message': 'No new data specified in request body.'}, 400
            
    @limiter.exempt
    @authenticated
    def put(self, requested_user_id = "", requested_user_detail = ""):
        return {'message': 'PUT requests are not supported for users. Use PATCH to update user details.'}, 400