from flask import Flask, request
from flask_restful import Api, Resource
import psycopg2
import requests

app = Flask("users")
api = Api(app)

conn = psycopg2.connect(dbname="userDB", user="root", password="postgres", host="users_persistence")


class Register(Resource):
    def post(self):
        request_data = request.json
        username = request_data.get('username')
        password = request_data.get('password')
        # Username and password should be provided
        if not username or not password:
            return {'message': 'Missing arguments. username and password are needed.', 'success': False}, 400
        curs = conn.cursor()
        # Check if user already exists with this username.
        curs.execute("SELECT * FROM users WHERE username = %s;", (username,))
        if curs.fetchone():
            return {'message': 'User already exists with this username', 'success': False}, 200
        # Create new user in the database
        curs.execute("INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id;", (username, password))
        user_id = curs.fetchone()[0]
        conn.commit()
        # Add a calendar for this user
        requests.post("http://calendars:5000/calendar/create", json={'user_id': user_id})
        return {'message': 'Register successful', 'success': True}, 200


class Exists(Resource):
    def get(self):
        request_data = request.json
        username = request_data.get('username')
        password = request_data.get('password')
        # Username and password should exist
        if not username or not password:
            return {'message': 'Missing arguments. username and password are needed.', 'success': False}, 400
        curs = conn.cursor()
        # Check for user to exist in database with given username andpassword
        curs.execute("SELECT * FROM users WHERE username = %s AND password = %s;", (username, password))
        if curs.fetchone() is not None:
            return {'success': True}, 200
        else:
            return {'success': False}, 200


class GetId(Resource):
    def get(self):
        request_data = request.json
        username = request_data.get('username')
        # Username should exist
        if not username:
            return {'message': 'Missing argument. username should be provided.', 'success': False}, 400
        curs = conn.cursor()
        # Get the id from a given user
        curs.execute("SELECT id FROM users WHERE username = %s;", (username,))
        result = curs.fetchone()
        if result is None:
            return {'message': 'User not found in database', 'success': False}, 200
        return {'success': True, 'id': result[0]}, 200


class GetUserName(Resource):
    def get(self):
        request_data = request.json
        id = request_data.get('id')
        # Id should be given
        if not id:
            return {'message': 'Missing argument. id should be provided.', 'success': False}, 400
        curs = conn.cursor()
        # Get the username from a given user
        curs.execute("SELECT username FROM users WHERE id = %s;", (id,))
        return {'success': True, 'username': curs.fetchone()[0]}, 200


api.add_resource(Register, '/user/register')
api.add_resource(Exists, '/user/exists')
api.add_resource(GetId, '/user/id')
api.add_resource(GetUserName, '/user/username')
