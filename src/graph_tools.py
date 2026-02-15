from datetime import datetime, timedelta
import pytz
import base64
from email.mime.text import MIMEText
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.auth import authenticate_google

# Initialize services
try:
    creds = authenticate_google()
    calendar_service = build('calendar', 'v3', credentials=creds)
    gmail_service = build('gmail', 'v1', credentials=creds)
except Exception as e:
    print(f"Warning: Failed to initialize Google services: {e}")
    calendar_service = None
    gmail_service = None

USER_TIMEZONE = pytz.timezone("Asia/Kolkata") 

def _localize_time(time_str: str) -> str:
    """Helper to localize time strings to ISO format."""
    if not time_str: return None
    clean_str = time_str.replace('"', '').replace("'", "").strip()
    
    dt_obj = None
    try:
        dt_obj = datetime.fromisoformat(clean_str.replace('Z', '+00:00'))
    except ValueError:
        try:
            dt_obj = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Handle date-only strings like "2026-02-11"
            try:
                dt_obj = datetime.strptime(clean_str, "%Y-%m-%d")
                dt_obj = dt_obj.replace(hour=9, minute=0)  # Default to 9:00 AM
            except ValueError:
                return None
    
    if dt_obj is None:
        return None
            
    if dt_obj.tzinfo is None:
        dt_aware = USER_TIMEZONE.localize(dt_obj)
    else:
        dt_aware = dt_obj
        
    return dt_aware.isoformat()

def _get_events_in_range(start_iso, end_iso):
    return calendar_service.events().list(
        calendarId='primary',
        timeMin=start_iso,
        timeMax=end_iso,
        singleEvents=True,
        orderBy='startTime'
    ).execute().get('items', [])

# --- EXPORTED TOOLS FOR LLM ---

@tool
def search_calendar_events(query: str, days: int = 7):
    """
    Search for calendar events matching a query within the next N days.
    Args:
        query: Search term (e.g., "flight", "meeting")
        days: Number of days to search ahead (default 7)
    """
    if not calendar_service: return "Calendar service unavailable."
    
    now = datetime.now(USER_TIMEZONE)
    end = now + timedelta(days=days)
    
    events = calendar_service.events().list(
        calendarId='primary',
        timeMin=now.isoformat(),
        timeMax=end.isoformat(),
        q=query,
        singleEvents=True,
        orderBy='startTime'
    ).execute().get('items', [])
    
    if not events:
        return "No matching events found."
        
    results = []
    for e in events:
        start = e['start'].get('dateTime', e['start'].get('date'))
        results.append(f"- {e.get('summary', 'No Title')} at {start}")
    
    return "\n".join(results)


@tool
def find_free_slots(anchor_time: str, duration_minutes: int = 30):
    """
    Finds free time slots starting from the anchor time.
    Args:
        anchor_time: ISO format string (e.g. 2023-10-27T14:00:00)
        duration_minutes: Duration of slots in minutes (default 30)
    """
    if not calendar_service: return "Calendar service unavailable."
    
    anchor_iso = _localize_time(anchor_time)
    if not anchor_iso:
        # Fallback to 'now' if anchor is invalid or missing
        start_dt = datetime.now(USER_TIMEZONE)
    else:
        start_dt = datetime.fromisoformat(anchor_iso)

    # Ensure we don't start in the past
    now = datetime.now(USER_TIMEZONE)
    if start_dt < now:
        start_dt = now

    # Round up to next 30 min interval
    if start_dt.minute % 30 != 0 or start_dt.second != 0:
        minutes_to_add = 30 - (start_dt.minute % 30)
        start_dt += timedelta(minutes=minutes_to_add)
        start_dt = start_dt.replace(second=0, microsecond=0)
        
    found_slots = []
    search_end = start_dt + timedelta(days=3)
    
    # Fetch busy events
    events = _get_events_in_range(start_dt.isoformat(), search_end.isoformat())
    busy_times = []
    for e in events:
        if 'dateTime' not in e['start']: continue 
        e_start = datetime.fromisoformat(e['start']['dateTime'])
        e_end = datetime.fromisoformat(e['end']['dateTime'])
        busy_times.append((e_start, e_end))
        
    # Search for slots (only within business hours: 9 AM – 7 PM)
    BUSINESS_HOUR_START = 9
    BUSINESS_HOUR_END = 19  # 7 PM
    
    current_slot = start_dt
    while len(found_slots) < 3 and current_slot < search_end:
        # Skip outside business hours
        if current_slot.hour < BUSINESS_HOUR_START:
            current_slot = current_slot.replace(hour=BUSINESS_HOUR_START, minute=0, second=0)
            continue
        if current_slot.hour >= BUSINESS_HOUR_END:
            # Jump to next day 9 AM
            current_slot = (current_slot + timedelta(days=1)).replace(
                hour=BUSINESS_HOUR_START, minute=0, second=0
            )
            continue
        
        slot_end = current_slot + timedelta(minutes=duration_minutes)
        
        # Ensure slot doesn't extend past business hours
        if slot_end.hour > BUSINESS_HOUR_END or (slot_end.hour == BUSINESS_HOUR_END and slot_end.minute > 0):
            current_slot = (current_slot + timedelta(days=1)).replace(
                hour=BUSINESS_HOUR_START, minute=0, second=0
            )
            continue
        
        is_conflict = False
        for b_start, b_end in busy_times:
            if current_slot < b_end and slot_end > b_start:
                is_conflict = True
                break
        
        if not is_conflict:
            nice_format = current_slot.strftime("%A, %b %d at %I:%M %p")
            found_slots.append(nice_format)
            current_slot = slot_end + timedelta(minutes=15) # Buffer
        else:
            current_slot += timedelta(minutes=30)
            
    if not found_slots:
        return "No free slots found in the next 3 days."
        
    return "Suggested Slots:\n" + "\n".join(found_slots)

# --- EMAIL HELPERS (For Graph Input) ---

def fetch_recent_emails(max_results=5):
    """
    Fetch the recent emails.
    """
    if not gmail_service: return []
    
    results = gmail_service.users().messages().list(
        userId="me",
        maxResults=max_results,
        q="to:me -from:me" # Optimized to just unread for now
    ).execute()

    messages = results.get("messages", [])
    full_email_objects = []

    for msg in messages:
        message = gmail_service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()
        
        full_email_objects.append(message) 

    return full_email_objects

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

    body = ""
    if "data" in payload.get("body", {}):
        body = payload["body"]["data"]
    elif "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                body = part["body"]["data"]
                break
    
    if body:
        try:
            body = base64.urlsafe_b64decode(body).decode("utf-8", errors="ignore")
        except:
            body = ""

    return sender, subject, body
@tool
def send_gmail(recipient: str, subject: str, body: str):
    """
    Sends an email using Gmail.
    Args:
        recipient: Email address of the recipient
        subject: Subject line
        body: Email body content
    """
    if not gmail_service: return "Gmail service unavailable."
    
    try:
        msg = MIMEText(body)
        msg['to'] = recipient
        msg['subject'] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        
        gmail_service.users().messages().send(userId='me', body={'raw': raw}).execute()
        return "Email sent successfully."
    except Exception as e:
        return f"Error sending email: {e}"

@tool
def check_calendar_availability(start_time: str, end_time: str = None, duration_minutes: int = 60):
    """
    Checks if a specific time slot is free.
    Args:
        start_time: ISO format string (e.g. 2023-10-27T14:00:00)
        end_time: ISO format string (optional). If provided, overrides duration_minutes.
        duration_minutes: Duration in minutes (default 60, used if end_time is missing).
    """
    if not calendar_service: return "Calendar service unavailable."
    
    start_iso = _localize_time(start_time)
    if not start_iso: return "Invalid start date format."
    start_dt = datetime.fromisoformat(start_iso)

    # Determine End Time
    if end_time:
        end_iso = _localize_time(end_time)
        if not end_iso: return "Invalid end date format."
        end_dt = datetime.fromisoformat(end_iso)
    else:
        end_dt = start_dt + timedelta(minutes=duration_minutes)
    
    # Check for conflicts
    events = _get_events_in_range(start_dt.isoformat(), end_dt.isoformat())
    
    if events:
        # Format the conflict details nicely
        conflict_list = []
        for e in events:
            # Handle all-day events vs timed events
            s = e['start'].get('dateTime', e['start'].get('date'))
            title = e.get('summary', 'Busy')
            conflict_list.append(f"'{title}' at {s}")
            
        return f"BUSY. Conflict with: {', '.join(conflict_list)}"
    
    return f"FREE. Available from {start_dt.strftime('%H:%M')} to {end_dt.strftime('%H:%M')}."

# In src/graph_tools.py

@tool
def add_calendar_event(summary: str, start_time: str, end_time: str = None, duration_minutes: int = 60, description: str = ""):
    """
    Adds a new event to the calendar. Checks for duplicates first.
    """
    if not calendar_service: return "Calendar service unavailable."
    
    start_iso = _localize_time(start_time)
    if not start_iso: return f"Error: Could not parse start time '{start_time}'."
    start_dt = datetime.fromisoformat(start_iso)
    
    # Calculate End Time
    if end_time:
        end_iso = _localize_time(end_time)
        if not end_iso: return f"Error: Could not parse end time '{end_time}'."
        end_dt = datetime.fromisoformat(end_iso)
    else:
        end_dt = start_dt + timedelta(minutes=duration_minutes)

    # --- NEW: IDEMPOTENCY CHECK (Prevents Double Booking) ---
    # Search for existing events at this exact time
    existing_events = _get_events_in_range(start_dt.isoformat(), end_dt.isoformat())
    for e in existing_events:
        # If an event with the same title starts at the same time, skip it.
        if e.get('summary', '').strip().lower() == summary.strip().lower():
             return f"Event already exists: '{summary}' at {start_dt.strftime('%H:%M')}. (Skipped duplicate)"
    # --------------------------------------------------------

    tz_name = str(USER_TIMEZONE)
    event_body = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start_iso, 'timeZone': tz_name},
        'end': {'dateTime': end_dt.isoformat(), 'timeZone': tz_name},
    }
    
    try:
        event = calendar_service.events().insert(calendarId='primary', body=event_body).execute()
        duration_str = str(end_dt - start_dt)
        return f"Success: Booked '{summary}' ({duration_str}). Link: {event.get('htmlLink')}"
    except Exception as e:
        return f"Error creating event: {e}"