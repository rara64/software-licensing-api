from flask_restful import Resource
from modules.limiter import limiter

class healthcheck(Resource):
    @limiter.exempt
    def get(self):
        return {'message': 'API is up and running!'}, 200