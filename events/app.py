from flask import Flask, request
from flask_restful import Api, Resource
import psycopg2
import requests

app = Flask("events")
api = Api(app)

conn = psycopg2.connect(dbname="eventDB", user="root", password="postgres", host="events_persistence")


def getUsername(id):
    response = requests.get("http://users:5000/user/username", json={'id': id}).json()
    if response['success']:
        return response['username']
    return None


def getId(username):
    response = requests.get("http://users:5000/user/id", json={'username': username}).json()
    if response['success']:
        return response['id']
    return None


class ListPublicEvents(Resource):
    def get(self):
        curs = conn.cursor()
        # Retrieve information about all the public events
        curs.execute("SELECT title, event_date, organizer_id FROM events WHERE is_public = TRUE")
        result = []
        for row in curs.fetchall():
            # For each event, convert the date to readable text and get the username of the organizer
            organizer = getUsername(row[2])
            result.append((row[0], row[1].strftime('%d %B %Y'), organizer))
        return {'success': True, 'events': result}, 200


class CreateEvent(Resource):
    def post(self):
        request_data = request.json
        title, description, date, is_public, organizer = request_data.get('title'), request_data.get(
            'description'), request_data.get('date'), True if request_data.get(
            'publicprivate') == 'public' else False, request_data.get('organizer')
        # Title, date, organizer and publicity should be given
        if not title or not date or not organizer or is_public is None:
            return {'message': 'Missing arguments. title, date, organizer and publicity is needed.',
                    'success': False}, 400
        organizer_id = getId(organizer)
        # Check if the organizer with username exists and is present in the database
        if organizer_id is None:
            return {'message': 'Given user to create event with does not exist in the database.', 'success': False}, 200
        curs = conn.cursor()
        # Create the event in the database
        curs.execute(
            "INSERT INTO events (event_date, organizer_id, title, description, is_public) VALUES (%s, %s, %s, %s, %s) RETURNING id;",
            (date, organizer_id, title, description, is_public))
        event_id = curs.fetchone()[0]
        # Check if id is returned
        if event_id is None:
            return {'message': 'Something went wrong during creation of the event.', 'success': False}, 500
        conn.commit()
        return {'success': True, 'id': event_id}, 200


class InviteUser(Resource):
    def post(self):
        request_data = request.json
        event_id, username = request_data.get('event_id'), request_data.get('user')
        # event_id and username should be given
        if event_id is None or not username:
            return {'message': 'Missing arguments. the id of the event and username is needed.',
                    'success': False}, 400
        user_id = getId(username)
        # Check if the user with username exists and is present in the database
        if user_id is None:
            return {'message': 'Given user to invite does not exist in the database.', 'success': False}, 200
        curs = conn.cursor()
        # Check if user is already invited for this event
        curs.execute("SELECT 1 FROM event_invitations WHERE event_id = %s and user_id = %s;", (event_id, user_id))
        if curs.fetchone() is not None:
            return {'message': 'user is already invited to this event.', 'success': True}, 200
        # Create an invitation entry in the database
        curs.execute("INSERT INTO event_invitations (event_id, user_id) VALUES (%s, %s);", (event_id, user_id))
        conn.commit()
        return {'success': True}, 200


class ListInvites(Resource):
    def get(self):
        request_data = request.json
        username = request_data.get('username')
        # username should be given
        if not username:
            return {'message': 'Missing argument. the username is needed.', 'success': False}, 400
        user_id = getId(username)
        # Check if the user with username exists and is present in the database
        if user_id is None:
            return {'message': 'Given user to list invites for does not exist in the database.', 'success': False}, 200
        curs = conn.cursor()
        # Retrieve all events where the user is invited for
        curs.execute(
            "SELECT events.id, events.title, events.event_date, events.organizer_id, events.is_public FROM events INNER JOIN event_invitations ON events.id = event_invitations.event_id WHERE event_invitations.user_id = %s;",
            (user_id,))
        result = []
        for row in curs.fetchall():
            # For each event, convert the date to readable text and get the username of the organizer
            publicity = 'Public' if row[4] else 'Private'
            organizer = getUsername(row[3])
            result.append((row[0], row[1], row[2].strftime('%d %B %Y'), organizer, publicity))
        return {'success': True, 'invites': result}, 200


class AnswerInvite(Resource):
    def post(self):
        request_data = request.json
        username, event_id, participation = request_data.get('username'), request_data.get(
            'event_id'), request_data.get('participation').replace("'", "")
        # username, event_id, participation should be given
        if not username or event_id is None or not participation:
            return {'message': 'Missing arguments. the username, event_id and participation is needed.',
                    'success': False}, 400
        user_id = getId(username)
        # Check if the user with username exists and is present in the database
        if user_id is None:
            return {'message': 'Given user to process invite does not exist in the database.', 'success': False}, 200
        curs = conn.cursor()
        # Add participation for this user and remove invite in database
        curs.execute("INSERT INTO event_participation (event_id, user_id, response) VALUES (%s, %s, %s);",
                     (event_id, user_id, participation))
        curs.execute("DELETE FROM event_invitations WHERE event_id = %s and user_id = %s;", (event_id, user_id))
        # When the user participates, it should be added to his calendar
        if participation != "Dont Participate":
            requests.post("http://calendars:5000/calendar/addEvent", json={'event_id': event_id, 'user_id': user_id})
        conn.commit()
        return {'success': True}, 200


class EventInfo(Resource):
    def get(self):
        request_data = request.json
        username, event_id = request_data.get('username'), request_data.get('event_id')
        # username and event_id should be given
        if not username or event_id is None:
            return {'message': 'Missing arguments. the username and event_id is needed.', 'success': False}, 400
        curs = conn.cursor()
        # Retrieve the information about an event from the database
        curs.execute("SELECT title, event_date, organizer_id, is_public FROM events WHERE id = %s;", (event_id,))
        response = curs.fetchone()
        if response is None:
            return {'message': 'No event found.', 'success': False}, 200
        organizer = getUsername(response[2])
        result = [response[0], response[1].strftime('%d %B %Y'), organizer, 'Public' if response[3] else 'Private']
        participants = []
        # retrieve all participations for this event
        curs.execute("SELECT user_id, response FROM event_participation WHERE event_id = %s;", (event_id,))
        response = curs.fetchall()
        for participant in response:
            # For each participant, get the username and add the participation
            username = getUsername(participant[0])
            participants.append([username, participant[1]])
        result.append(participants)
        return {'event': result, 'success': True}, 200


class ListCalendarEvents(Resource):
    def get(self):
        request_data = request.json
        event_ids, user_id = request_data.get('event_ids'), request_data.get('user_id')
        # user_id and event_ids should be given
        if not user_id or event_ids is None:
            return {'message': 'Missing arguments. the user_id and event_ids is needed.', 'success': False}, 400
        curs = conn.cursor()
        result = []
        for event_id in event_ids:
            # For each event, get the information from the database and add in a correct format to the result
            curs.execute("SELECT title, event_date, organizer_id, is_public FROM events WHERE id = %s;", (event_id,))
            response = curs.fetchone()
            organizer = getUsername(response[2])
            curs.execute("SELECT response FROM event_participation WHERE event_id = %s and user_id = %s;",
                         (event_id, user_id))
            participation = curs.fetchone()[0]
            result.append((event_id, response[0], response[1].strftime('%d %B %Y'), organizer, participation,
                           'Public' if response[3] else 'Private'))
        return {'events': result, 'success': True}, 200


api.add_resource(ListPublicEvents, '/event/public')
api.add_resource(CreateEvent, '/event/create')
api.add_resource(InviteUser, '/event/invite')
api.add_resource(ListInvites, '/event/invites')
api.add_resource(AnswerInvite, "/event/participation")
api.add_resource(EventInfo, '/event/info')
api.add_resource(ListCalendarEvents, '/event/calendar')
