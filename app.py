import streamlit as st
import time
import sqlite3
import os
from datetime import datetime
from langgraph.checkpoint.sqlite import SqliteSaver

from src.db import EmailDatabase
# from src.graph_agent import build_graph, fetch_recent_emails, extract_email_parts
from src.graph import build_graph, fetch_recent_emails, extract_email_parts

# --- SETUP ---
st.set_page_config(page_title="Ambient Email Agent", page_icon="📧", layout="wide")

# 1. Initialize DB
if "db" not in st.session_state:
    st.session_state.db = EmailDatabase()

# 2. Initialize Persistent Graph
if "graph" not in st.session_state:
    # Create checkpoint file if not exists
    conn = sqlite3.connect("data/checkpoints.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    st.session_state.graph = build_graph(checkpointer)

# 3. Initialize Widget Versions (For resetting text areas)
if "widget_versions" not in st.session_state:
    st.session_state.widget_versions = {}

# --- CSS STYLING ---
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 6px; font-weight: 500; }
    .stDeployButton {display:none;}
    /* Status indicators */
    .status-dot {height: 10px; width: 10px; background-color: #4CAF50; border-radius: 50%; display: inline-block;}

    /* Sidebar Header Styling */
    .sidebar-header {
        margin-bottom: 2rem;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        padding-bottom: 1rem;
    }
    .sidebar-header h3 {
        margin: 0;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Status Indicators (Glowing Dots) */
    .status-indicator {
        height: 10px;
        width: 10px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }
    .status-live { background-color: #00FF87; box-shadow: 0 0 10px #00FF87; }
    .status-paused { background-color: #FF6B6B; box-shadow: 0 0 5px #FF6B6B; }
    
    /* Dividers */
    .divider {
        height: 1px;
        background-color: rgba(255,255,255,0.1);
        margin: 1.5rem 0;
    }
    
    /* Stats Panels */
    .stats-panel {
        background-color: rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 10px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .stats-number {
        font-size: 1.5rem;
        font-weight: 700;
        color: #ffffff;
    }
    .stats-label {
        font-size: 0.8rem;
        color: rgba(255,255,255,0.6);
    }
    /* Metric Containers */
    div[data-testid="stMetric"] {
        background-color: #3a3a3a;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #E5E7EB;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    # --- HEADER ---
    st.markdown("""
    <div class="sidebar-header">
        <h3>🤖 Ambient Agent</h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)
    
    # --- STATUS PANEL ---
    st.markdown("### 🔍 System Status")
    auto_fetch = st.toggle("**Auto-Fetch Mode**", value=True, help="Enable real-time email monitoring")
    
    if auto_fetch:
        st.markdown("""
        <div style="margin: 0.5rem 0 1.5rem 0; padding: 10px; background: rgba(0, 255, 135, 0.1); border-radius: 8px;">
            <span class="status-indicator status-live"></span>
            <strong style="color: #00FF87;">LIVE MONITORING</strong>
            <p style="margin: 0.5rem 0 0 0; color: rgba(255,255,255,0.6); font-size: 0.85rem;">
                Actively scanning for new emails
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="margin: 0.5rem 0 1.5rem 0; padding: 10px; background: rgba(255, 107, 107, 0.1); border-radius: 8px;">
            <span class="status-indicator status-paused"></span>
            <strong style="color: #FF6B6B;">MANUAL MODE</strong>
            <p style="margin: 0.5rem 0 0 0; color: rgba(255,255,255,0.6); font-size: 0.85rem;">
                Manual control enabled
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # --- QUICK ACTIONS ---
    st.markdown("### ⚡ Quick Actions")
    
    if st.button("🔄 **Sync Now**", use_container_width=True, type="primary"):
        st.session_state.last_fetch = 0
        st.toast("Manual sync initiated...", icon="🔄")
        time.sleep(0.5)
        st.rerun()
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # --- STATISTICS ---
    # Safe retrieval of stats to prevent crashes
    try:
        all_emails_stat = st.session_state.db.get_all_emails()
        total_emails = len(all_emails_stat)
        drafts_pending = len([e for e in all_emails_stat if e['status'] == 'draft'])
    except:
        total_emails = 0
        drafts_pending = 0
    
    st.markdown("### 📊 Statistics")
    
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.markdown(f"""
        <div class="stats-panel" style="text-align: center;">
            <div class="stats-number">{total_emails}</div>
            <div class="stats-label">Total Processed</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_stat2:
        st.markdown(f"""
        <div class="stats-panel" style="text-align: center;">
            <div class="stats-number">{drafts_pending}</div>
            <div class="stats-label">Pending Review</div>
        </div>
        """, unsafe_allow_html=True)
    
    # --- SYNC STATUS ---
    if "last_fetch" not in st.session_state:
        st.session_state.last_fetch = 0
    
    if st.session_state.last_fetch > 0:
        fetch_time = datetime.fromtimestamp(st.session_state.last_fetch).strftime("%H:%M:%S")
        st.caption(f"🕐 **Last sync:** {fetch_time}")
    else:
        st.caption("🕐 **Last sync:** Never")
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # --- PREFERENCES ---
    with st.expander("⚙️ **Agent Preferences**", expanded=False):
        try:
            prefs = st.session_state.db.get_all_preferences()
            st.code(prefs, language="json")
        except AttributeError:
            st.error("Database configuration required")
            if st.button("Initialize Database", use_container_width=True):
                if os.path.exists("email_agent.db"):
                    os.remove("email_agent.db")
                st.session_state.db = EmailDatabase()
                st.rerun()
    
    st.markdown("""
    <div style="margin-top: 2rem; text-align: center;">
        <p style="color: rgba(255,255,255,0.4); font-size: 0.75rem;">
            Neural Core • v2.1.0 • Active
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- LOGIC: FETCH & PROCESS ---
def sync_emails():
    """Fetches ONLY new emails and runs initial graph."""
    db = st.session_state.db
    graph = st.session_state.graph
    
    try:
        # Check if DB is healthy
        db.get_all_emails()
    except:
        return False # Fail silently in loop, or handle error

    try:
        # Fetch recent emails
        gmail_messages = fetch_recent_emails(max_results=15)
        new_count = 0
        
        for msg in gmail_messages:
            eid = msg['id']
            # Persistence Check: Skip if already in DB
            if db.email_exists(eid): continue
            
            new_count += 1
            sender, subject, body = extract_email_parts(msg)
            
            # --- CRITICAL FIX: SAVE IMMEDIATELY ---
            # Save as 'processing' BEFORE running the graph.
            # This prevents double-booking if the graph crashes later.
            db.save_email(
                eid, sender, subject, body, 
                "processing", {}, ""
            )
            
            try:
                # Run Graph
                inputs = {
                    "email_id": eid, "sender": sender, "subject": subject, "body": body,
                    "messages": [], "user_decision": "pending", "status": "processing"
                }
                config = {"configurable": {"thread_id": eid}}
                
                for event in graph.stream(inputs, config): pass
                
                # Get Result
                final_state = graph.get_state(config)
                values = final_state.values
                
                # Determine Final Status
                status = "processing"
                # Check next steps or decisions to determine status
                if final_state.next and "human_review" in final_state.next:
                    status = "draft"
                elif values.get("triage_decision") == "IGNORE":
                    status = "ignored"
                elif values.get("triage_decision") == "NOTIFY":
                    status = "notify"
                
                # Update the existing record with the result
                db.update_state(eid, values, status)
                
            except Exception as e:
                print(f"⚠️ Error processing email {eid}: {e}")
                # Optional: Update status to 'error' so you can see it in UI
                # db.update_state(eid, {}, "error")
                continue
            
        if new_count > 0:
            st.toast(f"📥 {new_count} New Emails Processed!", icon="🔔")
            return True
            
    except Exception as e:
        print(f"Sync Error: {e}")
    return False

# --- UI: DISPLAY & ACTIONS ---

# Load Data with Auto-Fix
try:
    all_emails = st.session_state.db.get_all_emails()
except:
    st.warning("Rebuilding database...")
    st.session_state.db = EmailDatabase()
    st.rerun()

drafts = [e for e in all_emails if e['status'] == 'draft']
notifs = [e for e in all_emails if e['status'] == 'notify']
ignored = [e for e in all_emails if e['status'] == 'ignored' or e['status'] == 'discarded']
sent = [e for e in all_emails if e['status'] == 'sent']

# --- DASHBOARD ---
st.title("Inbox Dashboard")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Pending Actions", len(drafts))
col2.metric("Notifications", len(notifs))
col3.metric("Sent", len(sent))
col4.metric("Total Processed", len(all_emails))

st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    f"📝 Needs Review ({len(drafts)})",
    f"🔔 Notifications",
    f"🚫 Ignored",
    f"📤 Sent History",
    f"📨 All Mails",
])

# === TAB 1: DRAFTS ===
with tab1:
    if not drafts: st.info("No active drafts.")
    
    for email in drafts:
        eid = email['id']
        state = email['graph_state']
        config = {"configurable": {"thread_id": eid}}
        
        with st.container(border=True):
            st.subheader(email['subject'])
            st.caption(f"From: {email['sender']}")
            
            c1, c2 = st.columns(2)
            c1.text_area("Original", email['body'], height=200, disabled=True, key=f"orig_{eid}")
            
            # Dynamic Draft Loading
            d_text = state.get("draft_body", "")
            # Fallback
            if not d_text and state.get("messages"):
                from langchain_core.messages import AIMessage
                for m in reversed(state["messages"]):
                    if isinstance(m, AIMessage) and m.content:
                        d_text = m.content
                        break

            # Versioning for refresh
            current_ver = st.session_state.widget_versions.get(eid, 0)
            draft_key = f"draft_{eid}_{current_ver}"
            
            edited_draft = c2.text_area("Draft (Editable)", value=d_text, height=200, key=draft_key)

            # Actions
            b1, b2 = st.columns([1, 1])
            
            if b1.button("🚀 Approve & Send", key=f"send_{eid}", type="primary"):
                with st.spinner("Sending..."):
                    graph = st.session_state.graph
                    # Inject User Edits + Decision
                    graph.update_state(config, {
                        "draft_body": edited_draft, 
                        "user_decision": "approve"
                    })
                    try:
                        for event in graph.stream(None, config): pass
                        final = graph.get_state(config)
                        st.session_state.db.update_state(eid, final.values, "sent")
                        st.success("Sent!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

            if b2.button("🗑️ Discard", key=f"del_{eid}"):
                graph = st.session_state.graph
                graph.update_state(config, {"user_decision": "reject"})
                for event in graph.stream(None, config): pass
                st.session_state.db.update_state(eid, graph.get_state(config).values, "discarded")
                st.rerun()
            
            # Feedback
            with st.form(key=f"fb_{eid}"):
                fb = st.text_input("Request Changes")
                if st.form_submit_button("Revise"):
                    if fb:
                        graph = st.session_state.graph
                        graph.update_state(config, {
                            "user_decision": "feedback", 
                            "user_feedback": fb
                        })
                        for event in graph.stream(None, config): pass
                        
                        # Save & Increment Version to Refresh Text Area
                        st.session_state.db.update_state(eid, graph.get_state(config).values)
                        st.session_state.widget_versions[eid] = current_ver + 1
                        st.rerun()

# === OTHER TABS ===
with tab2:
    for e in notifs:
        with st.expander(f"📢 **{e['subject']}**", expanded=False):
            st.caption(f"**From:** {e['sender']}")
            st.caption(f"**Subject:** {e['subject']}")
            st.markdown("---")
            st.text(e['body'])

with tab3:
    for e in ignored:
        with st.expander(f"**{e['subject']}**", expanded=False):
            st.caption(f"**From:** {e['sender']}")
            st.caption(f"**Subject:** {e['subject']}")
            st.markdown("---")
            st.text(e['body'])

with tab4:
    for email in sent:
        with st.expander(f"**{email['subject']}**", expanded=False):
            st.caption(f"**To:** {email['sender']}")
            st.caption(f"**Subject:** {email['subject']}")
            st.markdown("---")
            st.text(email['body'])

with tab5:
    st.markdown("### 📨 Complete Inbox History")
    for email in all_emails:
        # Determine badge style
        status = email['status'].upper()
        badge_class = "badge-ignore"
        if status == 'DRAFT': badge_class = "badge-draft"
        elif status == 'SENT': badge_class = "badge-sent"
        elif status == 'NOTIFY': badge_class = "badge-notify"
        
        with st.expander(f"**{email['subject']}**"):
            st.caption(f"**From:** {email['sender']}")
            st.caption(f"**Subject:** {email['subject']}")
            st.markdown("---")
            
            # Show original body
            st.caption("Incoming Message:")
            # Use safe text handling
            body_preview = email.get('body', 'No Content')
            if len(body_preview) > 300:
                body_preview = body_preview[:300] + "..."
            st.markdown(f"> {body_preview}")
            
            # If there is a draft or sent reply, show it
            reply_text = email['graph_state'].get('draft_body')
            if reply_text:
                st.markdown("---")
                st.caption("Your Reply / Draft:")
                st.info(reply_text)

# --- 🚀 AUTOMATIC BACKGROUND REFRESH ---
# This block keeps the script running in a loop if Auto-Fetch is on.

if auto_fetch:
    # 1. Check if it is time to sync (e.g., every 5 seconds)
    if time.time() - st.session_state.last_fetch > 20:
        # Use an empty container to show activity without full reload flashing
        # with st.sidebar:
        #     with st.spinner("Checking for new mail..."):
        found_new = sync_emails()
        
        st.session_state.last_fetch = time.time()
        
        # If new mail was found, we MUST rerun to update the list
        if found_new:
            st.rerun()
            
    # 2. Heartbeat: Wait a bit, then rerun to keep the loop going
    # This ensures the app doesn't "stop" and checks again in 2 seconds
    time.sleep(5)
    st.rerun()