import os
import json
from datetime import datetime
from typing import TypedDict, List
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
# We do NOT import MemorySaver here anymore, we pass it in from app.py

from src.db import EmailDatabase
from src.graph_tools import (
    check_calendar_availability, find_free_slots, add_calendar_event,
    send_gmail, fetch_recent_emails, extract_email_parts
)

if "GROQ_API_KEY" not in os.environ:
    from dotenv import load_dotenv
    load_dotenv()

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
db = EmailDatabase()

class EmailState(TypedDict):
    email_id: str
    sender: str
    subject: str
    body: str
    triage_decision: str
    summary: str
    draft_body: str
    draft_subject: str
    draft_to: str
    user_decision: str
    user_feedback: str
    messages: List[BaseMessage]
    status: str

def _learn_from_feedback(feedback: str):
    """
    Analyzes feedback to see if it should be saved as a long-term preference.
    Called silently when an email is approved.
    """
    if not feedback: return

    print(f"🧠 Analyzing feedback for long-term memory: {feedback}")
    sys_msg = """Analyze the user's feedback instructions from this successful email session.
    Extract any GENERAL, LONG-TERM preferences that should apply to FUTURE emails.
    
    Feedback: "{feedback}"
    
    Rules:
    1. If feedback is specific to this email (e.g. "Change time to 5pm"), return {{ "preference": null }}.
    2. If general (e.g. "Always sign off as Bob", "No emojis"), return {{ "preference": "The rule" }}.
    
    Return JSON only."""
    
    try:
        res = llm.invoke(sys_msg.replace("{feedback}", feedback))
        content = res.content.strip().replace("```json", "").replace("```", "")
        if "{" in content: 
            content = content[content.find("{"):content.rfind("}")+1]
            data = json.loads(content)
            pref = data.get("preference")
            if pref:
                print(f"💡 SAVING PREFERENCE: {pref}")
                # Create a unique key for the rule
                key = f"rule_{datetime.now().timestamp()}"
                db.add_preference(key, pref)
    except Exception as e:
        print(f"Learning error: {e}")


# --- NODES ---
def triage_node(state: EmailState):
    print(f"--- Triage: {state.get('subject')} ---")
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    
    # Defensive check
    subject = state.get('subject', 'No Subject')
    body = state.get('body', '')
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert AI Executive Assistant.
            Your goal is to triage incoming emails into specific category
            
            ### CATEGORY DEFINITIONS:
            1. **IGNORE**: Automated newsletters, marketing, receipts, system logs, or spam.
            2. **NOTIFY**: Any emails I missed (which has date of past and importatnt), Any notices of exams or etc from university or school, informational emails where NO reply is expected (e.g., shipping updates, "FYI" memos, broad company announcements, "OTP"s).
            3. **RESPOND**: Emails that require a reply or action. This INCLUDES:
            - Invitations (Parties, Weddings, Meetings) that need an RSVP.**
            - Direct questions asked to Sanjay.
            - Scheduling requests.
            - Personal messages requiring acknowledgement.
        Return JSON: {{ "category": "..." }}"""),
        ("human", "Subject: {subject}\nBody: {body}")
    ])
    try:
        response = (prompt | llm).invoke({
            "current_date": current_date, "subject": subject, "body": body[:2000]
        })
        content = response.content.strip().replace("```json", "").replace("```", "")
        if "{" in content: content = content[content.find("{"):content.rfind("}")+1]
        category = json.loads(content).get("category", "NOTIFY").upper()
    except:
        category = "NOTIFY"
    
    return {"triage_decision": category}

# --- IN graph_agent.py ---

def process_notify_node(state: EmailState):
    print(f"--- Processing Notification: {state.get('subject')} ---")
    
    tools = [add_calendar_event]
    llm_with_tools = llm.bind_tools(tools)
    
    # Updated Prompt: Explicitly asks for End Time / Duration extraction
    sys_msg = f"""You are a calendar automation assistant.
    Current Date: {datetime.now().strftime("%A, %B %d, %Y")}
    
    Task: Extract event details and book them.
    
    CRITICAL DURATION RULES:
    1. Look for **End Times** (e.g., "2pm - 4pm", "until 5:00"). 
       -> Use the `end_time` parameter in ISO format.
    2. Look for **Durations** (e.g., "for 2 hours", "30 min call").
       -> Use the `duration_minutes` parameter.
    3. If NEITHER is specified, assume 60 minutes.
    
    Example: "Meeting tomorrow from 2pm to 4pm" -> start="...T14:00:00", end="...T16:00:00"
    """
    
    messages = [
        SystemMessage(content=sys_msg),
        HumanMessage(content=f"Subject: {state['subject']}\nBody: {state['body']}")
    ]
    
    response = llm_with_tools.invoke(messages)
    
    booking_status = "No event found."
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call['name'] == "add_calendar_event":
                print(f"🗓️ Auto-booking: {tool_call['args']}")
                booking_status = add_calendar_event.invoke(tool_call['args'])
    
    return {
        "status": "notify_processed",
        "summary": f"{state.get('summary', '')}\n[Auto-Calendar]: {booking_status}"
    }

def draft_agent_node(state: EmailState):
    print("--- Drafting ---")
    
    long_term_prefs = db.get_all_preferences()
    current_feedback = state.get("user_feedback", "")
    
    # Bind improved tools
    tools = [check_calendar_availability, find_free_slots, add_calendar_event]
    llm_with_tools = llm.bind_tools(tools)
    
    sys_msg = f"""You are a helpful Executive Assistant.
    Current Date: {datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")}
    
    ===========
    🧠 MEMORY: {long_term_prefs}
    📝 INSTRUCTION: {current_feedback if current_feedback else "Reply appropriately."}
    ===========
    
    ### CALENDAR & DURATION RULES:
    1. **ALWAYS** check for specific durations or end times in the email.
       - "Meeting from 10 to 12" -> Check availability for 2 HOURS (`end_time` or 120 mins).
       - "Quick 15 min chat" -> Check 15 mins.
    2. **CHECK FIRST**: If a time is proposed, call `check_calendar_availability` with the CORRECT DURATION before drafting.
    3. **ISO FORMAT**: Convert all relative dates ("next Friday") to specific ISO timestamps (YYYY-MM-DDTHH:MM:SS).
    
    Draft the reply based on the tool results.
    """
    
    messages = [
        SystemMessage(content=sys_msg),
        HumanMessage(content=f"Sender: {state['sender']}\nSubject: {state['subject']}\nBody: {state['body']}")
    ]
    
    for _ in range(3):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        
        if not response.tool_calls:
            break
            
        for tool_call in response.tool_calls:
            t_name = tool_call['name']
            t_args = tool_call['args']
            print(f"🛠️ Tool Call: {t_name} args: {t_args}")
            
            tool_res = "Error"
            try:
                if t_name == "check_calendar_availability":
                    tool_res = check_calendar_availability.invoke(t_args)
                elif t_name == "find_free_slots":
                    tool_res = find_free_slots.invoke(t_args)
                elif t_name == "add_calendar_event":
                    tool_res = add_calendar_event.invoke(t_args)
            except Exception as e:
                tool_res = f"Error: {str(e)}"
                
            messages.append(ToolMessage(tool_call_id=tool_call['id'], content=str(tool_res)))

    final_text = messages[-1].content if messages else ""
    
    return {
        "draft_body": final_text,
        "draft_to": state['sender'],
        "draft_subject": f"Re: {state['subject']}",
        "messages": messages,
    }

def process_feedback_node(state: EmailState):
    print("--- Learning from Feedback ---")
    feedback = state.get("user_feedback", "")
    
    if feedback:
        # LLM extracts the rule
        sys_msg = """Analyze this feedback. Extract any LONG-TERM preference.
        Example: "Don't use emojis" -> Preference: "Never use emojis".
        Example: "Change 2pm to 3pm" -> No preference (Specific change).
        Return JSON: { "preference": "..." } or { "preference": null }"""
        
        try:
            res = llm.invoke([SystemMessage(content=sys_msg), HumanMessage(content=feedback)])
            # ... (Parse JSON logic) ...
            pref = data.get("preference")
            
            if pref:
                print(f"💡 LEARNING: {pref}")
                # SAVE TO DB
                key = f"pref_{datetime.now().timestamp()}"
                db.add_preference(key, pref)
        except Exception as e:
            print(f"Learning error: {e}")
            
    return {"status": "feedback_processed"}

def process_notify_node(state: EmailState):
    print(f"--- Processing Notification: {state.get('subject')} ---")
    
    # 1. Bind the add_calendar_event tool to the LLM
    tools = [add_calendar_event]
    llm_with_tools = llm.bind_tools(tools)
    
    # 2. Ask LLM to find an event
    sys_msg = f"""You are an intelligent calendar assistant.
    Current Date: {datetime.now().strftime("%A, %B %d, %Y")}
    
    Analyze the email. If it contains a **CONFIRMED SPECIFIC EVENT** with a date and time (e.g., "Webinar on Oct 5th at 2pm", "Flight confirmed for..."), book it immediately using the tool.
    
    Rules:
    - Do NOT book vague events ("Let's meet sometime next week").
    - Do NOT book if the email is just asking for availability.
    - Only book if it's a notification/confirmation.
    - Convert relative dates (e.g., "tomorrow") to ISO format based on Current Date.
    """
    
    messages = [
        SystemMessage(content=sys_msg),
        HumanMessage(content=f"Subject: {state['subject']}\nBody: {state['body']}")
    ]
    
    response = llm_with_tools.invoke(messages)
    
    # 3. Execute tool if LLM decided to call it
    booking_status = "No event found."
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call['name'] == "add_calendar_event":
                print(f"🗓️ Auto-booking event detected: {tool_call['args']}")
                booking_status = add_calendar_event.invoke(tool_call['args'])
    
    # Update state to reflect what happened
    return {
        "status": "notify_processed",
        "summary": f"{state.get('summary', '')}\n[Auto-Calendar]: {booking_status}"
    }

def send_email_node(state: EmailState):
    print(f"--- Sending to {state['draft_to']} ---")
    
    # 1. LEARN: Process feedback here (Side Effect)
    if state.get("user_feedback"):
        _learn_from_feedback(state["user_feedback"])
    
    # 2. ACT: Send the email
    try:
        res = send_gmail.invoke({
            "recipient": state['draft_to'],
            "subject": state['draft_subject'],
            "body": state['draft_body']
        })
        return {"status": "sent"}
    except:
        return {"status": "error"}

# --- GRAPH ---
def build_graph(checkpointer=None):
    workflow = StateGraph(EmailState)
    
    # Add Nodes
    workflow.add_node("triage", triage_node)
    workflow.add_node("process_notify", process_notify_node) # NEW NODE
    workflow.add_node("draft", draft_agent_node)
    workflow.add_node("process_feedback", process_feedback_node)
    workflow.add_node("send", send_email_node)
    
    # Placeholder nodes
    workflow.add_node("ignore", lambda x: {"status": "ignored"})
    workflow.add_node("discard", lambda x: {"status": "discarded"})
    workflow.add_node("human_review", lambda x: x)

    # Entry
    workflow.set_entry_point("triage")
    
    # Conditional Edge from Triage
    def route_triage(state):
        d = state['triage_decision']
        if d == "IGNORE": return "ignore"
        if d == "NOTIFY": return "process_notify" # CHANGED: Route to new node
        return "draft"

    workflow.add_conditional_edges("triage", route_triage, 
        {"ignore": "ignore", "process_notify": "process_notify", "draft": "draft"})
    
    # Edge from Process Notify -> End
    workflow.add_edge("process_notify", END)
    
    # Draft -> Review
    workflow.add_edge("draft", "human_review")
    
    # Review Logic
    def route_human(state):
        d = state.get("user_decision", "pending")
        if d == "approve": return "send"
        if d == "reject": return "discard"
        if d == "feedback": return "process_feedback"
        return "__end__"

    workflow.add_conditional_edges("human_review", route_human,
        {"send": "send", "discard": "discard", "process_feedback": "process_feedback"})
    
    workflow.add_edge("process_feedback", "draft")
    workflow.add_edge("send", END)
    workflow.add_edge("ignore", END)
    workflow.add_edge("discard", END)
    
    return workflow.compile(checkpointer=checkpointer, interrupt_before=["human_review"])