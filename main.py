from __future__ import print_function

from typing import List

from datetime import datetime, time, timedelta
import pytz
from dataclasses import dataclass
import json
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file credentials.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

EVENTS_SERVICE = None
TASKS_SERVICE = None


@dataclass()
class Event:
    id: str
    summary: str
    start_date: str
    end_date: str
    link: str
    status: str
    description: str

    def to_json(self):
        return self.__dict__


@dataclass()
class Calendar:
    id: str
    summary: str
    description: str
    time_zone: str


@dataclass()
class TaskList:
    id: str
    self_link: str
    title: str


@dataclass()
class Task:
    id: str
    due: str
    notes: str
    self_link: str
    title: str
    parent: str
    position: str
    '''
    parent: parent task identifier. This field is omitted if it is a top-level task.
    position: string indicating the position of the task among its sibling tasks under the same parent task or 
      at the top level. If this string is greater than another task's corresponding position string according to 
      lexicographical ordering, the task is positioned after the other task under the same parent task (or at the top
      level)
      '''


def init():
    global EVENTS_SERVICE, TASKS_SERVICE
    """Shows basic usage of the Google Calendar API.
       Prints the start and name of the next 10 events on the user's calendar.
       """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        EVENTS_SERVICE = build('calendar', 'v3', credentials=creds)
        TASKS_SERVICE = build('tasks', 'v1', credentials=creds)

    except HttpError as error:
        print('An error occurred: %s' % error)


def test_query():
    now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')

    try:
        events_result = EVENTS_SERVICE.events().list(calendarId='primary', timeMin=now,
                                                     maxResults=10,
                                                     singleEvents=True,
                                                     orderBy='startTime'
                                                     ).execute()
        with open('out.json', 'w') as o:
            o.write(json.dumps(events_result))

        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
            return

        # Prints the start and name of the next 10 events
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])

    except HttpError as error:
        print('An error occurred: %s' % error)


def map_event_to_dto(event) -> Event:
    return Event(summary=event['summary'],
                 start_date=event['start'].get('dateTime', event['start'].get('date')),
                 end_date=event['end'].get('dateTime', event['start'].get('date')),
                 link=event['htmlLink'],
                 status=event['status'],
                 id=event['id'],
                 description=event.get('description', ''))


def map_calendar_to_dto(calendar) -> Calendar:
    return Calendar(id=calendar['id'],
                    summary=calendar['summary'],
                    description=calendar.get('description', ''),
                    time_zone=calendar['timeZone'])


def map_task_list_to_dto(task_list) -> TaskList:
    return TaskList(id=task_list['id'],
                    self_link=task_list['selfLink'],
                    title=task_list.get('title', ''))


def map_task_to_dto(task) -> Task:
    return Task(id=task['id'],
                due=task.get('due', ''),
                notes=task.get('notes', ''),
                self_link=task['selfLink'],
                title=task['title'],
                parent=task.get('parent', ''),
                position=task.get('position', ''))


def get_start_date_time(tz='UTC') -> str:
    next_day_starts = datetime.combine(datetime.now(), time.min) + timedelta(days=1)
    formatted = next_day_starts.astimezone(pytz.timezone(tz)).isoformat()
    print(f'begin day time for tz {tz}: {formatted}')
    return formatted


def get_end_date_time(tz='UTC') -> str:
    next_day_starts = datetime.combine(datetime.now(), time.max) + timedelta(days=1)
    formatted = next_day_starts.astimezone(pytz.timezone(tz)).isoformat()
    print(f'begin day time for tz {tz}: {formatted}')
    return formatted


def get_next_day_events(calendar_id='primary', tz='Ukraine/Kiev') -> List[Event]:
    start_of_day = get_start_date_time(tz)
    end_of_day = get_end_date_time(tz)

    try:
        events_result = EVENTS_SERVICE.events().list(calendarId=calendar_id, timeMin=start_of_day, timeMax=end_of_day,
                                                     singleEvents=True, orderBy='startTime', timeZone=tz).execute()
        events = [map_event_to_dto(event).to_json() for event in events_result['items']]
        if not events:
            print(f'No upcoming events found for {calendar_id}.')
            return []
        return events

    except HttpError as error:
        print('An error occurred: %s' % error)

    # map events to simple model


def get_tasks_lists() -> List[TaskList]:
    tasks = TASKS_SERVICE.tasklists().list().execute()['items']
    with open('task.json', 'w') as f:
        f.write(json.dumps(tasks))
    return [map_task_list_to_dto(task) for task in tasks]


def get_tasks(list_id: str, date_from: str, date_to: str) -> List[Task]:
    res = TASKS_SERVICE.tasks().list(tasklist=list_id, dueMax=date_to, dueMin=date_from).execute()
    return [map_task_to_dto(task) for task in res['items']]


def get_user_calendars() -> List[Calendar]:
    try:
        return [map_calendar_to_dto(cal) for cal in EVENTS_SERVICE.calendarList().list().execute()['items']]

    except HttpError as error:
        print('An error occurred: %s' % error)


def main(tz='UTC'):
    init()
    # get_events()
    get_all_tasks(tz)


def get_all_tasks(tz='UTC'):
    date_from = get_start_date_time(tz)
    date_to = get_end_date_time(tz)
    tasks_lists = get_tasks_lists()
    tasks = []
    for tl in tasks_lists:
        tasks.extend(get_tasks(tl.id, date_from, date_to))

    with open('out_next_day_tasks.json', 'w') as o:
        o.write(json.dumps(tasks))
    print(tasks)


def get_events():
    calendars = get_user_calendars()
    events = []
    for calendar in calendars:
        events.extend(get_next_day_events(calendar.id, calendar.time_zone))
    with open('out_next_day_short.json', 'w') as o:
        o.write(json.dumps(events))
    print(events)


if __name__ == '__main__':
    main()
