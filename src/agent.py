import json
from src.gemini import llm_call
from src.groq_llm import llm_call_1
from src.tools import add_event, delete_event, send_email, check_availability, find_free_slots
from src.db import MemoryManager
from datetime import datetime
from langsmith import traceable

memory = MemoryManager()

def learn_from_feedback(feedback_text):
    """
    Uses LLM to distill raw feedback into a reusable rule.
    """
    prompt = f"""
    Analyze this user feedback: "{feedback_text}"
    
    Does this contain a general preference or rule for future emails?
    If yes, extract it as a short Key-Value pair.
    
    Examples:
    - "Don't use 'Dear' anymore" -> Key: "Greeting", Value: "Do not use 'Dear'"
    - "I'm always busy on Mondays" -> Key: "Schedule", Value: "Busy on Mondays"
    
    Return ONLY valid JSON: {{ "key": "...", "value": "..." }}
    If no general rule exists, return {{ "key": "NONE", "value": "" }}
    """
    
    try:
        # We assume llm_call is available or use self.client.generate_content
        response = llm_call_1(prompt)
        data = json.loads(response.replace("```json", "").replace("```", ""))
        
        if data["key"] != "NONE":
            memory.save_preference(data["key"], data["value"])
            return f"Learned: {data['key']} -> {data['value']}"
    except Exception as e:
        print(f"Learning failed: {e}")
    return ""

@traceable(name="triage")
def traige_email(email_text: str) -> str:
    prompt = f"""
    You are an expert AI Executive Assistant.
    Your goal is to triage incoming emails into specific category
    
    ### CATEGORY DEFINITIONS:
    1. **IGNORE**: The Replies i gave (start with Re: subject) or has the same mail as me Automated newsletters, marketing, receipts, system logs, or spam.
    2. **NOTIFY**: informational emails where NO reply is expected (e.g., shipping updates, "FYI" memos, broad company announcements, "OTP"s).
    3. **RESPOND**: Emails that require a reply or action. This INCLUDES:
    - Invitations (Parties, Weddings, Meetings) that need an RSVP.**
    - Direct questions asked to Sanjay.
    - Scheduling requests.
    - Personal messages requiring acknowledgement.


    Email:
    {email_text}

    Only return the category.
    """
    return llm_call_1(prompt)

from datetime import datetime as dt


import json
import datetime as dt

def create_draft_reply(gmail_service, calendar_service, sender: str, subject: str, body: str) -> str:
    
    now = dt.datetime.now()
    current_context = now.strftime("%A, %B %d, %Y at %H:%M") 
    
    # --- STEP 1: EXTRACT TIME & DURATION ---
    # We ask for JSON to capture duration (e.g., "30 mins", "2 hours")
    extraction_prompt = f"""
    ### Role
    You are an Executive Scheduler. Extract event details from the email below.

    ### Context
    Today is: {current_context}

    ### Rules
    1. **Start Time:** ISO 8601 format. If date is present but time missing, assume 09:00:00.
    2. **Duration:** Extract duration in **minutes** (integer). 
       - Default to 60 if not specified. 
       - "Quick chat" = 30 mins. "Lunch" = 60 mins.
    3. **Timezone:** Detect timezone (e.g., EST, IST) if mentioned.

    ### Email Body
    "{body}"

    ### Output Format (Strict JSON)
    {{
        "start_time": "YYYY-MM-DDTHH:MM:SS" or null,
        "duration_minutes": 60,
        "timezone_context": "Detected timezone or None"
    }}
    """
    
    try:
        raw_extraction = llm_call_1(extraction_prompt).strip().replace('```json', '').replace('```', '')
        event_data = json.loads(raw_extraction)
        
        event_time = event_data.get("start_time")
        duration = event_data.get("duration_minutes", 60)
        
    except Exception as e:
        print(f"Extraction Error: {e}")
        event_time = None
        duration = 60

    # --- STEP 2: CHECK AVAILABILITY & GENERATE CONTEXT ---
    calendar_context = "No specific time mentioned."
    conflict_event = None
    is_free = True
    suggested_slots = []
    
    # Flag to determine if we should allow auto-booking
    can_auto_book = False 

    if event_time:
        print(f"\n📅 Requested: {event_time} ({duration} mins)")
        
        # Check specific slot
        availability = check_availability(calendar_service, event_time, duration)
        
        if availability["status"] == "BUSY":
            is_free = False
            conflict_event = availability["event"]
            can_auto_book = False
            
            print(f"❌ Conflict detected: {conflict_event['summary']}")
            
            # PROACTIVE: Find alternatives
            suggested_slots = find_free_slots(calendar_service, event_time, duration)
            slots_str = ", ".join(suggested_slots)
            
            calendar_context = (
                f"STATUS: BUSY at requested time ({event_time}). "
                f"Conflict: '{conflict_event['summary']}'. "
                f"SUGGESTED ALTERNATIVES found in calendar: {slots_str}. "
                "Action: Politely decline the specific time and offer the alternatives."
            )
        else:
            is_free = True
            can_auto_book = True
            calendar_context = (
                f"STATUS: FREE at requested time ({event_time}). "
                "Action: You can accept this meeting."
            )
    
    # --- STEP 3: DRAFTING EMAIL ---
    user_preferences = memory.get_all_preferences()
    current_feedback = ""

    while True:
        draft_prompt = f"""
        You are an Email Assistant. Write a reply based on the context.

        ### EMAIL DATA
        Sender: {sender}
        Subject: {subject}
        Body: {body}

        ### CALENDAR INTELLIGENCE
        {calendar_context}
        (If alternatives are suggested, list them clearly in the email body).

        ### PREFERENCES
        {user_preferences}
        
        ### USER FEEDBACK
        {current_feedback}

        ### OUTPUT JSON
        {{
            "To": "{sender}",
            "Subject": "Re: {subject}",
            "Body": "Email body..."
        }}
        """

        print("\n--- Generating Draft... ---")
        try:
            response_json = llm_call_1(draft_prompt).replace('```json', '').replace('```', '')
            reply_data = json.loads(response_json)
        except Exception:
            print("Error parsing draft JSON. Retrying...")
            continue

        print(f"\nDRAFT PREVIEW:\nTo: {reply_data['To']}\nSubject: {reply_data['Subject']}\nBody:\n{reply_data['Body']}\n")
        
        # --- STEP 4: USER ACTION ---
        prompt_text = "Action (yes / no / replace / [feedback]): "
        if not can_auto_book and event_time:
             prompt_text = "Action (yes [send only] / no / replace / [feedback]): "
             
        user_choice = input(prompt_text).strip().lower()

        # 1. SEND EMAIL
        if user_choice in ["yes", "y"]:
            if can_auto_book and event_time and event_time != "NONE":
                print(f"📅 Booking event: '{subject}' for {duration} mins...")
                result = add_event(
                    calendar_service, 
                    f"Meeting: {sender}", 
                    event_time,           
                    duration              
                )
                print(f"Calendar Result: {result}")
            
            elif not can_auto_book and event_time:
                print("ℹ️ Sending email proposing times (Calendar NOT booked - waiting for their reply).")
            
            print(f"📨 Sending email to {reply_data['To']}...")
            send_email(
                gmail_service, 
                reply_data['To'], 
                reply_data['Subject'], 
                reply_data['Body']
            )
            return "Success: Email Sent."

        # 2. REPLACE CONFLICT
        elif "replace" in user_choice:
            if conflict_event:
                print(f"🔄 Replacing '{conflict_event['summary']}'...")
                delete_event(calendar_service, conflict_event['id'])
                
                # Now add the new event
                add_event(calendar_service, f"Meeting with {sender}", event_time, duration)
                
                # Update context for the loop (so we can regenerate the email saying "Yes")
                calendar_context = "STATUS: FREE (User cleared conflict). You MUST ACCEPT the invitation now."
                current_feedback += " Conflict resolved. Rewrite email to Accept."
                can_auto_book = False # Already booked manually above, don't double book
            else:
                print("⚠️ No conflict to replace.")

        # 3. CANCEL
        elif user_choice in ["no", "n"]:
            return "Cancelled."

        # 4. FEEDBACK LOOP
        else:
            current_feedback += f"\n- User request: {user_choice}"

@traceable(name="notify")
def process_notify(sender: str, subject: str, body: str):
    """Processes the Notification and gives a short summary or finds important events"""
    
    now = datetime.now()
    current_context = now.strftime("%A, %B %d, %Y at %H:%M")

    prompt = f"""
    ### Role
    You are an expert Executive Assistant. Your goal is to process an incoming notification email.
    
    ### Context
    Today is: {current_context}
    (Use this to resolve relative dates like "tomorrow" or "next Friday".)

    ### Input Data
    Subject: "{subject}"
    Body: "{body[:2000]}" 

    ### Tasks
    1. **Summarize**: Create a crisp, 5-10 word status update (e.g., "Amazon package arriving tomorrow").
    2. **Extract Event**: Check if this notification implies a calendar event (e.g., a flight, a webinar, a bill due date).
       - If a date is mentioned for a future event, extract it.
       - Use business logic (e.g., "Dinner" ~ 7 PM, "Meeting" ~ 9 AM-5 PM) if time is ambiguous.

    ### Output Format (Strict JSON Only)
    {{
        "summary": "The 5-10 word summary string",
        "event_found": true/false,
        "event_date": "YYYY-MM-DDTHH:MM:SS" or null,
        "reasoning": "Brief explanation of date calculation"
    }}
    """

    summary = llm_call_1(prompt).strip()

    try:
        # Clean potential markdown
        clean_text = summary.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        
        return {
            "summary": data.get("summary", "No summary available"),
            "event_found": data.get("event_found", False),
            "event_date": data.get("event_date"), # Will be None (null) if no event
            "original_subject": subject
        }
        
    except json.JSONDecodeError:
        # Fallback if LLM fails
        return {
            "summary": subject, # Fallback to subject line
            "event_found": False,
            "event_date": None,
            "original_subject": subject
        }
    

@traceable(name="draft_reply_generation")
def generate_reply_json(
    sender: str,
    subject: str,
    body: str,
    calendar_context: str,
    preferences: dict
):
    prompt = f"""
    You are a professional Email Assistant for Sanjay Sanapala.

    Sender: {sender}
    Subject: {subject}
    Body: {body}

    Calendar Context:
    {calendar_context}

    User Preferences:
    {preferences}

    Return STRICT JSON ONLY:
    {{
      "To": "{sender}",
      "Subject": "Re: {subject}",
      "Body": "Professional reply"
    }}
    """

    response = llm_call_1(prompt)

    if not response or not response.strip():
        raise ValueError("LLM returned empty response")

    clean = (
        response
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON from LLM.\nRaw response:\n{response}"
        ) from e
