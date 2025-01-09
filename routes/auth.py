from flask_restful import Resource, request
from modules.authentication import generate_token
from config import config
from modules.limiter import limiter
import bcrypt
import pyotp

class auth(Resource):
    def __init__(self, db_client):
        self.db_client = db_client

    """
    Acquire a JWT token to use the API
    /auth POST

    {
        "username":""
        "password":""
    }
    """
    @limiter.limit(f"{config.AUTH_LIMITER_PER_HOUR} per hour | {config.AUTH_LIMITER_PER_DAY} per day")
    def post(self):
        data = request.get_json()
        username = data.get("username")
        password = data.get("password")

        try:
            if username and password:
                user = self.db_client[config.USERS_COLLECTION].find_one({"username": username})
                if user:
                    hashed_password = user.get("password")
                    if bcrypt.checkpw(bytes(password, 'utf-8'), hashed_password):

                        # 2FA for admin user / if enabled
                        if str(user.get("_id")) == config.ADMIN_ID and config.ADMIN_OTP_SECRET.strip() != "":
                            otp = data.get("otp")
                            if otp:
                                totp = pyotp.TOTP(config.ADMIN_OTP_SECRET)
                                if str(otp) != str(totp.now()):
                                     raise Exception
                            else:
                                raise Exception
                        
                        token = generate_token(str(user.get("_id")))
                        return {'message': 'Token was successfully generated.', 'data': token}, 200
                
            raise Exception
        except:
            return {'message': 'Credentials are invalid.'}, 401