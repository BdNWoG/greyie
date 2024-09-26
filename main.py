from flask import Flask, redirect, url_for, session, render_template, request
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a random secret key
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Replace with the path to your OAuth 2.0 credentials JSON file
CLIENT_SECRETS_FILE = "credentials.json"

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
API_SERVICE_NAME = 'calendar'
API_VERSION = 'v3'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/authorize')
def authorize():
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)
    
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')

    session['state'] = state

    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    # Specify the state when creating the flow in the callback so that it can be validated
    state = session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    # Use the authorization server's response to fetch the OAuth 2.0 tokens
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    # Store credentials in the session
    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

    return redirect(url_for('greyed_calendar'))


@app.route('/greyed_calendar')
def greyed_calendar():
    # Load credentials from the session
    if 'credentials' not in session:
        return redirect('authorize')

    credentials = google.oauth2.credentials.Credentials(
        **session['credentials'])

    # Initialize the Google Calendar API
    service = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)

    # Fetch events from the user's primary calendar
    now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=100, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    greyed_out_events = []

    # Grey out event details
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        greyed_out_events.append({
            'start': start,
            'end': end,
            'summary': 'Busy'  # Replace actual event titles with 'Busy'
        })

    # Save this greyed-out calendar somewhere (for demo purposes, we'll skip the database)
    # You would typically save this to a database or a file.

    # Render the greyed-out calendar and create a shareable link (e.g., to a public page)
    return render_template('calendar.html', events=greyed_out_events)


if __name__ == '__main__':
    app.run('localhost', 8080, debug=True)
