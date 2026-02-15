DRAFT_TESTS = [
    {
        "inputs": {
            "sender": "hr@techcorp.com",
            "subject": "URGENT: Final Interview Reschedule for Senior Engineer Position",
            "body": "Dear Sanjay, Due to unexpected schedule changes with our Director of Engineering, we need to reschedule your final interview. The original panel is only available Friday at 2 PM. This is time-sensitive as we have another candidate in final stages. Please confirm if you can make this new time, or suggest alternatives within the next 24 hours. We appreciate your flexibility. Best, Sarah Chen - Talent Acquisition Lead",
            "calendar_context": "You are BUSY from 1 PM to 4 PM on Friday (Quarterly Planning with executive team). You have 30-minute buffer before and after."
        },
        "expected": {
            "intent": "decline and propose alternative time",
            "must_include": ["unable to attend", "Friday at 2 PM", "conflict", "alternative time", "available"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "alex.manager@company.com",
            "subject": "ACTION REQUIRED: Q3 Planning Slides for Thursday's Executive Review",
            "body": "Sanjay, Following up from our sync - I need your updated projections, risk assessment, and team capacity analysis slides by 5 PM today. The deck goes to VP Ops at 6 PM sharp. John mentioned you might have the raw data - can you include as appendix? Let me know if you need an extension, but please note this is for Thursday's board prep. Thanks, Alex",
            "calendar_context": "You have back-to-back client meetings from 10 AM to 4:30 PM. You have 45 minutes free at 4:45 PM before your next commitment."
        },
        "expected": {
            "intent": "acknowledge and confirm deadline",
            "must_include": ["acknowledge", "by 5 PM", "will provide slides", "available at 4:45 PM", "deadline"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "mark.ceo@startup-partner.io",
            "subject": "Critical: Integration Roadblock Discussion - Need 60 mins this week",
            "body": "Sanjay, We've hit major integration roadblocks that could delay the Q4 launch. Need your technical input for about an hour. I'm flexible tomorrow morning or Wednesday afternoon. This is urgent - we have a board update Friday and need to decide on path forward. Can you also bring the latest analytics dashboard? If you're not the right contact, please redirect to appropriate technical lead. Mark Thompson, CEO",
            "calendar_context": "You are FREE between 9 AM and 11 AM tomorrow. You have a hard stop at 11 AM for investor meeting."
        },
        "expected": {
            "intent": "accept meeting and suggest time",
            "must_include": ["available tomorrow", "9 AM to 10 AM", "accept", "bring the latest analytics dashboard", "hard stop at 11 AM"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "audit@finance-legal.company.com",
            "subject": "AUDIT FINDING: Invoice #INV-2024-789 - Immediate Response Required",
            "body": "Mr. Kumar, Our external auditors have flagged Invoice #INV-2024-789 for $45,670 with three discrepancies: 1) No SOW in records 2) Vendor not in approved list 3) Procurement workflow deviation. As the approver, please provide by Friday COB: 1) Justification memo 2) Signed SOW copy 3) Technical evaluation document. This is compliance-critical with board reporting Monday. CC: General Counsel & CFO.",
            "calendar_context": "No calendar event detected, but you have 'Prepare audit materials' in your task list with deadline tomorrow EOD."
        },
        "expected": {
            "intent": "acknowledge and provide status",
            "must_include": ["acknowledge", "working on", "by Friday COB", "audit materials", "provide requested documents"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "priya.techlead@company.com",
            "subject": "PRODUCTION INCIDENT: Payment module 40% failure - need immediate code review",
            "body": "Sanjay, Production alert: Payment processing shows 40% failure post-2PM deploy. Error traces point to your auth service refactor. Need you to: 1) Review PR #457 immediately 2) Join war room (Zoom: company.com/incident) 3) Fix must deploy by 6 PM PST for SLA. SRE team on standby. Mobile: 555-0123 if urgent. Priya (Tech Lead)",
            "calendar_context": "You are in 'Do Not Disturb' focus session until 5 PM for strategic planning. No other meetings scheduled after 5 PM."
        },
        "expected": {
            "intent": "acknowledge and set expectation",
            "must_include": ["acknowledge", "focus session until 5 PM", "join war room at 5 PM", "review PR #457", "fix by 6 PM PST"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "emily.recruiter@top-tech-firm.com",
            "subject": "FORMAL OFFER PACKAGE: Principal Engineer Role - Discussion Required",
            "body": "Dear Sanjay, Following your successful interviews, we're excited to extend a formal offer for Principal Engineer. The package includes base, equity, and signing bonus. Need 45 minutes this week to walk through details and answer questions. I'm available Thursday afternoon or Friday morning. Please bring any competing offers for comparison. We aim to close by week's end. Best, Emily Rodriguez - Senior Tech Recruiter",
            "calendar_context": "You are FREE on Thursday 2-4 PM and Friday 10 AM-12 PM. You have a dentist appointment Thursday 3 PM."
        },
        "expected": {
            "intent": "propose meeting time",
            "must_include": ["propose", "Friday 10 AM", "45 minutes", "thank you for the offer", "available", "dentist appointment"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "security-team@trust.compliance.io",
            "subject": "SECURITY BREACH INVESTIGATION: Your account flagged in access logs",
            "body": "Security Incident #INC-7894: Your credentials were used to access restricted financial systems from unrecognized IP (Berlin, DE) on Tuesday 2 AM EST. Required: 1) Confirm if this was you 2) If not, list all your devices 3) Timeline of your activities Tuesday 1-3 AM EST 4) Any VPN usage. Response needed within 2 hours per security protocol. This is a P1 incident.",
            "calendar_context": "No calendar event detected, but you have 'Security training' scheduled for next week."
        },
        "expected": {
            "intent": "request clarification",
            "must_include": ["request clarification", "confirm if this was me", "provide details of my activities", "security incident", "within 2 hours"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "rajesh.ceo@yourcompany.com",
            "subject": "IMMEDIATE: Board member wants 15-minute sync before market close",
            "body": "Sanjay, Mary Chen (Board Member) just called - she's concerned about the Q3 projections and wants to connect with you directly before market closes today. Can you spare 15 minutes anytime between 2-3:30 PM? This takes priority over other meetings. Please confirm ASAP. Rajesh - CEO",
            "calendar_context": "You are FREE from 2:15 PM to 2:45 PM. You have a client call at 3 PM that cannot be moved."
        },
        "expected": {
            "intent": "accept meeting with priority",
            "must_include": ["available at 2:15 PM", "15-minute sync", "priority", "client call at 3 PM", "confirm"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "vendor-relations@procurement.company.com",
            "subject": "CONTRACT RENEWAL: AWS Enterprise Agreement - Your approval needed",
            "body": "Sanjay, The AWS Enterprise Agreement (EA) renews in 14 days. Current spend: $245k/month. New 3-year commitment offers 18% discount but includes 20% minimum annual growth clause. Need your technical sign-off by EOD tomorrow. Options: 1) Accept new EA 2) Negotiate terms (2-week extension available) 3) Split across multiple providers. Finance and legal teams copied for urgency.",
            "calendar_context": "You have vendor meetings scheduled tomorrow 10 AM-12 PM. You are free 3-5 PM tomorrow."
        },
        "expected": {
            "intent": "acknowledge and provide status",
            "must_include": ["acknowledge", "will review", "sign-off by EOD tomorrow", "available tomorrow afternoon", "options"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "noreply@system-alerts.company.com",
            "subject": "AUTOMATED: Your credentials expire in 24 hours - mandatory reset",
            "body": "SYSTEM ALERT: Your domain credentials will expire in 24 hours (Thursday, 2 PM EST). Failure to reset will lock you out of all corporate systems including email, VPN, and production environments. Click here to reset now: https://auth.company.com/reset. This is an automated message - do not reply. For issues, contact IT help desk.",
            "calendar_context": "You have meetings from 9 AM to 6 PM tomorrow with only 15-minute breaks."
        },
        "expected": {
            "intent": "acknowledge and confirm action",
            "must_include": ["acknowledge", "will reset credentials", "before expiration", "during a break", "IT help desk"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "global-team@company-uk.co.uk",
            "subject": "Meeting Request: London team sync (your 9 PM, our 2 PM)",
            "body": "Hello from London team! We need to sync on the cross-region deployment scheduled for Saturday. Our team is available your Thursday 9-10 PM (our Friday 2-3 PM). Could you join? We'll cover: 1) Rollback procedures 2) Communication plan 3) On-call rotation. If this time doesn't work, we can do your Friday early morning (our Friday late afternoon). Cheers, Liam - UK Engineering Lead",
            "calendar_context": "You are FREE Thursday 8-11 PM. You have family dinner scheduled at 8:30 PM."
        },
        "expected": {
            "intent": "accept meeting and suggest time",
            "must_include": ["accept", "Thursday 9-10 PM", "family dinner at 8:30", "available after dinner", "rollback procedures"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "legal@merger-company.com",
            "subject": "CONFIDENTIAL: Due diligence materials required - M&A transaction",
            "body": "CONFIDENTIAL & ATTORNEY-CLIENT PRIVILEGED. As part of the acquisition of TechStart Inc., we need you to provide: 1) All architecture diagrams for System X 2) Code quality metrics for past year 3) List of technical debt items 4) Team competency matrix. Required by Monday 9 AM EST. This material will be shared with acquiring company's technical team under NDA. Do not discuss this request outside this email chain.",
            "calendar_context": "You have 'Prepare M&A materials' blocked Friday 1-5 PM. No other conflicts."
        },
        "expected": {
            "intent": "acknowledge and confirm deadline",
            "must_include": ["acknowledge", "will provide by Monday 9 AM", "time blocked Friday afternoon", "confidential", "due diligence"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "support-premium@enterprise-vendor.com",
            "subject": "Escalated: P1 Support Ticket #78945 - System Integration Failure",
            "body": "Escalation Notice: Your company's integration with our API platform is experiencing 100% failure rate since 4:32 AM EST. Impact: All customer transactions failing. Our engineers suspect breaking change in your latest deployment. Required: 1) Immediate rollback to previous version 2) Conference bridge with your engineers 3) Root cause analysis within 4 hours per SLA. Bridge: 888-555-0192, PIN: 78945. Urgency: Critical Business Impact.",
            "calendar_context": "You are on vacation but have 'monitor critical systems' as remote work agreement."
        },
        "expected": {
            "intent": "acknowledge and provide status",
            "must_include": ["acknowledge", "on vacation but monitoring", "will coordinate rollback", "join conference bridge", "root cause analysis"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "university-alumni@stanford.edu",
            "subject": "Invitation: Guest lecture for CS 229 - Machine Learning course",
            "body": "Dear Sanjay, Prof. Rodriguez has invited you to give a guest lecture for CS 229 on 'Production ML Systems' next month. We can schedule either Nov 15 or 22, 10:30 AM-12 PM IST. This would be virtual via Zoom. Honorarium: $2,000. Please let us know if either date works, and if you'd like to suggest a different topic. Many students cited your papers in their applications! Best, Stanford CS Department",
            "calendar_context": "You are traveling for conferences both weeks but have flexible remote work days."
        },
        "expected": {
            "intent": "propose meeting time",
            "must_include": ["accept invitation", "available on Nov 15", "10:30 AM-12 PM IST", "thank you", "Production ML Systems"],
            "tone": "professional"
        }
    },
    {
        "inputs": {
            "sender": "system@calendar-bot.company.com",
            "subject": "Auto-detected: Meeting conflict with 3 recurring events next week",
            "body": "CALENDAR BOT: I detected that your newly scheduled 'Project Kickoff' (Mon 10 AM-12 PM) conflicts with: 1) Weekly Team Sync (Mon 10-11 AM) 2) Engineering Leadership (Mon 11 AM-12 PM) 3) 1:1 with Manager (alternate weeks, next is Monday). Suggested actions: A) Move kickoff to Tuesday slot B) Shorten to 90 mins C) Delegate attendance. Please review and adjust. This is an automated alert from Calendar Optimizer.",
            "calendar_context": "You have all three conflicting meetings as recurring with high priority flags."
        },
        "expected": {
            "intent": "request clarification",
            "must_include": ["request clarification", "conflict with recurring meetings", "suggested actions", "please advise", "high priority"],
            "tone": "professional"
        }
    }
]

TRIAGE_TESTS = [
    # NOTIFY Category (Informational, no response needed
    {
        "email": "Your flight AI-104 from Delhi to Mumbai on 15th Dec is confirmed. Departure: 18:45 IST. Check-in opens 3 hours before. PNR: XYZ789. Download your boarding pass at https://airindia.in/checkin",
        "expected": "NOTIFY"
    },
    {
        "email": "A transaction of ₹15,750.00 was made on your HDFC Credit Card ending 4587 at AMAZON.IN at 14:23 IST. Available limit: ₹2,34,500.00. If not recognized, call 1800-1234 immediately.",
        "expected": "NOTIFY"
    },
    {
        "email": "Dear Sanjay, your Aadhaar update request #AU789456 has been approved. Your updated Aadhaar card will be delivered within 15 working days. Track at uidai.gov.in/track/789456. This is an auto-generated message.",
        "expected": "NOTIFY"
    },
    {
        "email": "Company All Hands Meeting scheduled for Friday, 10:30 AM IST. Agenda: Q4 results and restructuring announcement. Attendance mandatory for all employees. Venue: Main Auditorium, Building 3.",
        "expected": "NOTIFY"
    },
    
    # RESPOND Category (Requires action/reply)
    {
        "email": "Hi Sanjay, we need to discuss the Q3 budget overrun. Can we meet tomorrow between 3-5 PM IST? I've booked Conference Room 2, but need your confirmation. Also, please bring the vendor cost breakdown sheets.",
        "expected": "RESPOND"
    },
    {
        "email": "Interview Invitation: Your application for Senior Data Scientist has been shortlisted. Available slots: 23rd Oct (10 AM, 2 PM, 4 PM IST) or 24th Oct (11 AM, 3 PM IST). Please confirm preferred slot within 24 hours.",
        "expected": "RESPOND"
    },
    {
        "email": "Internal Audit Finding #IA-789: Your team's project expenses exceeded approved budget by 35%. Please provide detailed justification by EOD 18th Oct. Reply to this email with: 1) Root cause analysis 2) Corrective action plan 3) Revised projections.",
        "expected": "RESPOND"
    },
    {
        "email": "Quick question - Did you approve the AWS bill for ₹4,85,000? Finance needs your sign-off before 5 PM today to avoid service interruption. Also, can you clarify which cost center this should be charged to?",
        "expected": "RESPOND"
    },
    
    # IGNORE Category (Spam/Promotional/Auto)
    {
        "email": "🔥 LIMITED TIME OFFER! Get 80% OFF on Sony Headphones + FREE Delivery! Use code: DEAL80. Shop Now: electronicsdeals.in/sony-offer. Unsubscribe link at bottom.",
        "expected": "IGNORE"
    },
    {
        "email": "You have been selected for a free iPhone 15! Click here to claim your prize by completing a short survey. This offer expires in 2 hours. Terms and conditions apply.",
        "expected": "IGNORE"
    },
    {
        "email": "This email confirms your subscription to 'Digital Marketing Trends' newsletter. You'll receive weekly updates on SEO, social media, and advertising tips. To unsubscribe, click here.",
        "expected": "IGNORE"
    },
    
    # Edge Cases & Ambiguous Scenarios
    {
        "email": "Meeting minutes from today's 11 AM IST sync: 1) Project timeline moved by 2 weeks 2) Budget increased by 15% 3) Next review on 25th Oct. Please acknowledge receipt.",
        "expected": "RESPOND"  # Requires acknowledgement
    },
    {
        "email": "Your Zomato Gold membership has been auto-renewed for ₹999. Transaction ID: ZM789456. Membership valid till 15 Oct 2025. To cancel or raise dispute, contact support within 24 hours.",
        "expected": "NOTIFY"  # Information about completed transaction
    },
    {
        "email": "Congratulations! Your paper has been accepted at IEEE Conference 2024. Registration deadline: 30th Nov. Early bird fee: $500 until 15th Nov. Please complete registration to confirm your slot.",
        "expected": "RESPOND"  # Requires registration action
    },
    
    # Professional Context Specific
    {
        "email": "Dear Sanjay, your article has been published in our monthly tech magazine. View here: techmag.in/oct2024/sanjay-kumar. Please share with your network. Looking forward to your next submission!",
        "expected": "NOTIFY"
    },
    {
        "email": "Reminder: Team offsite at Lonavala this weekend. Departure: Saturday 7 AM from office. Packing list and itinerary attached. Please confirm dietary preferences by Thursday EOD.",
        "expected": "RESPOND"
    },
    {
        "email": "Exclusive Invitation: AWS Summit Delhi on 5th Nov. Network with cloud experts. Limited seats available. Register now at aws.events/summit-delhi. Not interested? Unsubscribe from partner emails.",
        "expected": "IGNORE"
    },
    
    # Personal/Family Context
    {
        "email": "Maa, I'll reach Bangalore tonight by 9:30 PM. Flight details sent separately. No need to pick me up, I'll take Uber. See you soon! - Rohit",
        "expected": "NOTIFY"
    },
    {
        "email": "Family function at cousin's house this Sunday at 6 PM. Address: 45, MG Road. Please confirm if you're coming and how many people. Need to arrange food accordingly.",
        "expected": "RESPOND"
    },
    {
        "email": "Your doctor appointment with Dr. Sharma is confirmed for tomorrow at 4:30 PM. Please arrive 15 minutes early with previous reports. Cancellation fee of ₹500 if cancelled within 24 hours.",
        "expected": "NOTIFY"
    },
]