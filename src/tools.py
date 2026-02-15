from googleapiclient.discovery import build
from src.gemini import llm_call
# from src.groq_llm import llm_call
import datetime
from src.auth import authenticate_google

creds = authenticate_google()
calendar_service = build('calendar', 'v3', credentials=creds)
gmail_service = build('gmail', 'v1', credentials=creds)

# ---------------- Calendar Tools
import datetime
from datetime import timedelta
import pytz

USER_TIMEZONE = pytz.timezone("Asia/Kolkata") 

def localize_time(time_str):
    """
    Parses a time string. 
    - If it has a timezone (e.g. Z or +05:30), keeps it.
    - If it is NAIVE (e.g. 14:00), assumes it is USER_TIMEZONE (IST).
    Returns an ISO 8601 string that Google Calendar accepts.
    """
    if not time_str:
        return None
        
    clean_str = time_str.replace('"', '').replace("'", "").strip()
    
    # 1. Parse string to datetime object
    try:
        # Try ISO format first (e.g. 2026-02-06T14:00:00)
        dt_obj = datetime.datetime.fromisoformat(clean_str.replace('Z', '+00:00'))
    except ValueError:
        try:
            # Fallback for "Space" separator (e.g. 2026-02-06 14:00:00)
            dt_obj = datetime.datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            print(f"❌ Date Parsing Error: Could not parse '{clean_str}'")
            return None

    # 2. Assign Timezone
    if dt_obj.tzinfo is None:
        # CRITICAL FIX: Treat naive time as LOCAL (IST), not UTC
        dt_aware = USER_TIMEZONE.localize(dt_obj)
        print(f"   ℹ️  Assumed Local Time ({USER_TIMEZONE}): {dt_aware}")
    else:
        # It already has a timezone, leave it alone
        dt_aware = dt_obj

    # 3. Return as ISO format (Google handles offsets like +05:30 perfectly fine)
    return dt_aware.isoformat()

def ensure_timezone(iso_time):
    """Ensures time string has a timezone offset. Defaults to UTC (Z) if missing."""
    if not iso_time: return None
    if not iso_time.endswith('Z') and '+' not in iso_time[-6:] and '-' not in iso_time[-6:]:
        return iso_time + 'Z'
    return iso_time

def get_events_in_range(service, start_iso, end_iso):
    """Helper to fetch raw events between two times."""
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_iso,
        timeMax=end_iso,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])

def check_availability(service, start_time_str, duration_minutes=60):
    """
    Checks if a specific slot is free using localized time logic.
    """
    # 1. Localize input to User Timezone (IST)
    start_iso = localize_time(start_time_str)
    if not start_iso:
        return {"status": "ERROR", "event": None}

    start_dt = datetime.datetime.fromisoformat(start_iso)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    
    # 2. Query Google Calendar
    events = get_events_in_range(service, start_dt.isoformat(), end_dt.isoformat())
    
    if events:
        return {"status": "BUSY", "event": events[0]}
    
    return {"status": "FREE", "event": None}

def find_free_slots(service, anchor_time_str, duration_minutes=30, num_slots=3):
    """
    Scans for free slots starting from anchor_time using localized logic.
    """
    # 1. Localize anchor time
    anchor_iso = localize_time(anchor_time_str)
    if not anchor_iso:
        # Fallback to 'now' if anchor is invalid
        start_dt = datetime.datetime.now(USER_TIMEZONE)
    else:
        start_dt = datetime.datetime.fromisoformat(anchor_iso)
    
    # 2. Ensure we don't start in the past
    now = datetime.datetime.now(USER_TIMEZONE)
    if start_dt < now:
        start_dt = now

    # 3. Round up to next 30 min interval
    if start_dt.minute % 30 != 0 or start_dt.second != 0:
        minutes_to_add = 30 - (start_dt.minute % 30)
        start_dt += timedelta(minutes=minutes_to_add)
        start_dt = start_dt.replace(second=0, microsecond=0)

    found_slots = []
    search_end = start_dt + timedelta(days=3)
    
    # 4. Fetch all events in search window
    all_events = get_events_in_range(service, start_dt.isoformat(), search_end.isoformat())
    
    # 5. Parse busy times (handling timezone consistency)
    busy_times = []
    for e in all_events:
        if 'dateTime' not in e['start']: continue # Skip all-day events
        
        # Google returns ISO strings with offsets; fromisoformat parses them correctly
        e_start = datetime.datetime.fromisoformat(e['start']['dateTime'])
        e_end = datetime.datetime.fromisoformat(e['end']['dateTime'])
        busy_times.append((e_start, e_end))

    # 6. Iterate slots
    current_slot = start_dt
    while len(found_slots) < num_slots and current_slot < search_end:
        slot_end = current_slot + timedelta(minutes=duration_minutes)
        
        # Optional: Working Hours Filter (e.g., 9 AM - 6 PM)
        # if not (9 <= current_slot.hour < 18):
        #     # Skip to next day 9 AM
        #     current_slot = (current_slot + timedelta(days=1)).replace(hour=9, minute=0)
        #     continue

        is_conflict = False
        for b_start, b_end in busy_times:
            # Overlap check
            if current_slot < b_end and slot_end > b_start:
                is_conflict = True
                break
        
        if not is_conflict:
            # Format: "Friday, Feb 06 at 02:00 PM"
            nice_format = current_slot.strftime("%A, %b %d at %I:%M %p")
            found_slots.append(nice_format)
            # Add buffer (15 mins) before next suggestion
            current_slot = slot_end + timedelta(minutes=15)
        else:
            # If busy, try next 30 min increment
            current_slot += timedelta(minutes=30)

    return found_slots

def add_event(service, summary, start_time_str, duration_minutes=60):
    start_iso = localize_time(start_time_str)
    if not start_iso:
        return "Error: Invalid Start Time Format"

    start_dt = datetime.datetime.fromisoformat(start_iso)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    
    end_iso = end_dt.isoformat()

    print(f"DEBUG: Creating Event -> {summary}")
    print(f"DEBUG: Start: {start_iso}") 
    print(f"DEBUG: End:   {end_iso}")

    event_body = {
        'summary': summary,
        'start': {'dateTime': start_iso},
        'end': {'dateTime': end_iso},
    }
    
    try:
        event = service.events().insert(calendarId='primary', body=event_body).execute()
        link = event.get('htmlLink')
        print(f"✅ Event Created Successfully: {link}")
        return f"Success: Event created at {link}"
    except Exception as e:
        error_msg = f"❌ API Error creating event: {str(e)}"
        print(error_msg)
        return error_msg


def delete_event(service, event_id):
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting event: {e}")
        return False

# -------------------- Email tools
import base64
from email.mime.text import MIMEText
from googleapiclient.errors import HttpError

def fetch_recent_emails(service, max_results=5):
    """
    Fetch the recent emails.
    """
    results = service.users().messages().list(
        userId="me",
        maxResults=max_results,
        q="to:me -from:me"
    ).execute()

    messages = results.get("messages", [])
    full_email_objects = []

    for msg in messages:
        message = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()
        
        full_email_objects.append(message) 

    return full_email_objects

def extract_body(payload: dict) -> str:
    """
    Extract the body from the email returned by gmail
    """
    body = ""

    if "data" in payload.get("body", {}):
        body = payload["body"]["data"]

    elif "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                body = part["body"]["data"]
                break

    if body:
        return base64.urlsafe_b64decode(body).decode("utf-8", errors="ignore")

    return ""


def extract_email_parts(message: dict):
    """
    Extract the email parts like sender, subject and body from returned value by gmail
    """
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    subject = ""
    sender = ""

    for h in headers:
        name = h.get("name", "").lower()
        if name == "subject":
            subject = h.get("value", "")
        elif name == "from":
            sender = h.get("value", "")

    body = extract_body(payload)

    return sender, subject, body

def format_email_for_llm(sender, subject, body):
    return f"Sender: {sender}\nSubject: {subject}\n\nBody:\n{body}\n".strip()

def send_email(service, recipient, subject, body):
        """Sends the email immediately."""
        try:
            message = MIMEText(body)
            message['to'] = recipient
            message['subject'] = subject
            
            # Encode the message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            body = {'raw': raw}
            
            # Call Gmail API 'send' endpoint
            sent_message = service.users().messages().send(userId="me", body=body).execute()
            print(f"🚀 Email Sent! Message Id: {sent_message['id']}")
            return sent_message
        except HttpError as error:
            print(f"An error occurred sending email: {error}")
            return None

def search_gmail(service, query, get_all=False, max_results=5):
    """
    Search Gmail using pagination to retrieve all matching messages.
    """
    full_emails = []
    next_page_token = None
    
    try:
        while True:
            # Call the API with the nextPageToken if it exists
            results = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=500 if get_all else max_results,
                pageToken=next_page_token
            ).execute()

            messages = results.get("messages", [])
            
            # Fetch full content for this batch
            for msg in messages:
                message = service.users().messages().get(
                    userId="me",
                    id=msg["id"],
                    format='full'
                ).execute()
                full_emails.append(message)

            # Check if we should stop
            next_page_token = results.get('nextPageToken')
            
            # Stop if:
            # 1. No more pages exist
            # 2. We only wanted a specific number (get_all=False)
            if not next_page_token or not get_all:
                break

        return full_emails, len(full_emails)
        
    except Exception as e:
        print(f"Error: {e}")
        return [], 0
    
import json
from datetime import date

def query_gmail_assistant(user_question):
    today = date.today().strftime("%Y/%m/%d")

    prompt = f"""
    You are an expert Translator for the Gmail API.
    Your goal is to convert a user's natural language question into a Gmail search query (parameter 'q').

    ### CONTEXT:
    - Today's Date: {today}
    - User: Sanjay Sanapala

    ### GMAIL QUERY SYNTAX CHEATSHEET:
    - Unread emails: "is:unread"
    - From specific person: "from:name@example.com" or "from:Name"
    - Subject contains: "subject:(meeting)"
    - Date range: "after:2024/01/01 before:2024/01/31"
    - Labels: "label:Work", "label:Updates"
    - Categories: "category:primary", "category:social", "category:promotions"
    - Exact phrase: "\"exact phrase\""

    ### EXAMPLES:
    User: "How many unread emails do I have?"
    Output: {{"query": "is:unread", "intention": "count"}}

    User: "Show me the latest email from Sanjay."
    Output: {{"query": "from:Sanjay", "intention": "list"}}

    User: "Any emails about the internship in the last 2 days?"
    Output: {{"query": "internship after:{today}", "intention": "list"}}

    ### INPUT:
    User: "{user_question}"

    ### OUTPUT (JSON ONLY):
    Return valid JSON with keys: "query" (the gmail search string) and "intention" (either "count" or "list").
    """

    response = llm_call(prompt)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"query": "", "intention": "error"}
    
def ask_gmail(service, query):
    print(f"User asking: '{query}'")

    res = query_gmail_assistant(query)
    gmail_query = res.get("query")
    intention = res.get("intention")

    print(f"Generated Query: '{gmail_query}' (Intention: {intention})")

    if not gmail_query:
        return "Sorry, I couldn't understand how to search for that"
    
    emails, count = search_gmail(service, gmail_query, max_results=500)

    if intention == "count":
        return f"I found approximately {count} emails matching your request"
    elif intention == "list":
        if not emails:
            return "No emails found matching that criteria."
        
        final_prompt = f"User asked: '{query}'.\nHere are the email details found:\n"

        for email in emails:
            sender, subject, body = extract_email_parts(email)
        
        final_prompt += "\n Answer the user's question naturally based on these emails."
        return llm_call(final_prompt)
    
# response = ask_gmail(service, "How many unread emails are there")
# print(response)