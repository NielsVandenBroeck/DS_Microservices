from flask import Flask, request
from flask_restful import Api, Resource
import psycopg2
import requests

app = Flask("calendars")
api = Api(app)
print("connecting to calendar DB")

conn = psycopg2.connect(dbname="calendarDB", user="root", password="postgres", host="calendars_persistence")


def getId(username):
    response = requests.get("http://users:5000/user/id", json={'username': username}).json()
    if response['success']:
        return response['id']
    return None


class CreateCalendar(Resource):
    def post(self):
        request_data = request.json
        user_id = request_data.get('user_id')
        # user_id should be given
        if user_id is None:
            return {'message': 'Missing argument. user_id is needed.', 'success': False}, 400
        curs = conn.cursor()
        # Create a new calendar in the database
        curs.execute("INSERT INTO calendars (user_id) VALUES (%s);", (user_id,))
        conn.commit()
        return {'success': True}, 200


class CalendarInfo(Resource):
    def get(self):
        request_data = request.json
        viewer_name, calendar_user_name = request_data.get('username'), request_data.get('calendar_user')
        # viewer_name, calendar_user_name should be given
        if not viewer_name or not calendar_user_name:
            return {'message': 'Missing arguments. viewer_name and calendar_user_name is needed.',
                    'success': False}, 400
        owner_id = getId(calendar_user_name)
        # Check if the owner with username exists and is present in the database
        if owner_id is None:
            return {'message': 'Given owner to watch calendar for does not exist in the database.',
                    'success': False}, 200
        curs = conn.cursor()
        # Retrieve the id of the owner
        curs.execute("SELECT id FROM calendars WHERE user_id = %s;", (owner_id,))
        calendar_id = curs.fetchone()[0]
        # If the viewer's and owner's name is the same, no check for permission is needed
        if viewer_name != calendar_user_name:
            viewer_id = getId(viewer_name)
            # Check if the viewer with username exists and is present in the database
            if viewer_id is None:
                return {'message': 'Given viewer to watch calendar does not exist in the database.',
                        'success': False}, 200
            # Check if the viewer had permission to watch calendar
            curs.execute("SELECT 1 FROM calendar_sharing WHERE calendar_id = %s AND viewer_id = %s;",
                         (calendar_id, viewer_id))
            shared = curs.fetchone()
            if not shared:
                return {'message': 'The viewer does not have permission to watch the calendar.', 'success': False}, 200
        # Retrieve all event_ids from the calendar to display
        curs.execute("SELECT event_id from calendar_events WHERE calendar_id = %s;", (calendar_id,))
        event_ids = [item[0] for item in curs.fetchall()]
        result = requests.get("http://events:5000/event/calendar",
                              json={'event_ids': event_ids, 'user_id': owner_id}).json()
        if result['success']:
            return {'calendar': result['events'], 'success': True}, 200
        else:
            return {'message': result['message'], 'success': False}, 500


class AddEvent(Resource):
    def post(self):
        request_data = request.json
        event_id, user_id = request_data.get('event_id'), request_data.get('user_id')
        # event_id, user_id should be given
        if event_id is None or user_id is None:
            return {'message': 'Missing arguments. user_id and event_id is needed.', 'success': False}, 400
        curs = conn.cursor()
        # Insert a link to the event for the calender in the database
        curs.execute(
            "INSERT INTO calendar_events (event_id, calendar_id) VALUES (%s,(SELECT id FROM calendars WHERE user_id = %s));",
            (event_id, user_id))
        conn.commit()
        return {'success': True}, 200


class ShareCalendar(Resource):
    def post(self):
        request_data = request.json
        calendar_user, shared_user = request_data.get('calendar_user'), request_data.get('shared_user')
        # calendar_user, shared_user should be given
        if not calendar_user or not shared_user:
            return {'message': 'Missing arguments. calendar_user and shared_user is needed.', 'success': False}, 400
        owner_id = getId(calendar_user)
        # Check if the owner_id with username exists and is present in the database
        if owner_id is None:
            return {'message': 'Given owner to share the calendar does not exist in the database.',
                    'success': False}, 400
        viewer_id = getId(shared_user)
        # Check if the viewer with username exists and is present in the database
        if viewer_id is None:
            return {'message': 'Given viewer to share the calendar with does not exist in the database.',
                    'success': False}, 200
        curs = conn.cursor()
        # Check if calendar is already shared with this user
        curs.execute(
            "SELECT 1 FROM calendar_sharing WHERE viewer_id = %s and calendar_id = (SELECT id FROM calendars WHERE user_id = %s);",
            (viewer_id, owner_id))
        if curs.fetchone() is not None:
            return {'message': 'Calendar is already shared with this user.', 'success': True}, 200
        # Create a calender sharing in the database for the given calendar and viewer
        curs.execute(
            "INSERT INTO calendar_sharing (viewer_id, calendar_id) VALUES (%s,(SELECT id FROM calendars WHERE user_id = %s));",
            (viewer_id, owner_id))
        conn.commit()
        return {'success': True}, 200


api.add_resource(CreateCalendar, '/calendar/create')
api.add_resource(CalendarInfo, '/calendar')
api.add_resource(AddEvent, '/calendar/addEvent')
api.add_resource(ShareCalendar, '/calendar/share')
