"""Static content for SkyArch: navigation, page copy, architecture views,
segment descriptions and the initiative library.

All *numbers* shown on the dashboard are computed from the dataset in
analytics.py — nothing here is a statistic.
"""

NAV_ITEMS = [
    {"label": "Overview", "icon": "grid", "endpoint": "overview"},
    {"label": "Data workspace", "icon": "database", "endpoint": "data_workspace"},
    {"label": "Service analytics", "icon": "chart", "endpoint": "service_analytics"},
    {"label": "Passenger segments", "icon": "users", "endpoint": "passenger_segments"},
    {"label": "Architecture", "icon": "layers", "endpoint": "architecture"},
    {"label": "Improvement roadmap", "icon": "route", "endpoint": "roadmap"},
]

PAGE_COPY = {
    "Data workspace": {
        "eyebrow": "Data operations",
        "title": "Passenger data workspace",
        "description": "Manage source data, validate quality, and prepare passenger records for analysis.",
    },
    "Service analytics": {
        "eyebrow": "Experience intelligence",
        "title": "Service quality analytics",
        "description": "Compare touchpoints, identify friction, and understand what drives satisfaction.",
    },
    "Passenger segments": {
        "eyebrow": "Passenger intelligence",
        "title": "Passenger segments",
        "description": "Explore how different traveler groups experience each stage of the journey.",
    },
    "Architecture": {
        "eyebrow": "Enterprise architecture",
        "title": "SkyArch architecture",
        "description": "Connect airline capabilities, data, applications, and technology with Zachman and TOGAF.",
    },
    "Improvement roadmap": {
        "eyebrow": "Transformation planning",
        "title": "Service improvement roadmap",
        "description": "Initiatives ranked by how much each service gap holds back overall satisfaction.",
    },
}

SEGMENT_INFO = {
    "Business travelers": {"color": "sky",
                           "description": "Passengers flying for work, where speed, Wi-Fi and digital boarding matter most."},
    "Personal travelers": {"color": "violet",
                           "description": "Leisure passengers focused on comfort, value and baggage."},
    "Loyal customers": {"color": "emerald",
                        "description": "Returning passengers with high service expectations."},
    "Delay-affected": {"color": "rose",
                       "description": "Passengers whose departure was delayed by 15 minutes or more."},
}

# Improvement initiative suggested for each service touchpoint (keyed by dataset column)
INITIATIVE_LIBRARY = {
    "Inflight wifi service": {"name": "Wi-Fi reliability pilot", "owner": "Inflight Ops"},
    "Departure/Arrival time convenient": {"name": "Schedule convenience review", "owner": "Network Planning"},
    "Ease of Online booking": {"name": "Booking flow redesign", "owner": "Digital & IT"},
    "Gate location": {"name": "Gate assignment optimisation", "owner": "Airport Ops"},
    "Food and drink": {"name": "Inflight menu refresh", "owner": "Catering"},
    "Online boarding": {"name": "Mobile boarding upgrade", "owner": "Digital & IT"},
    "Seat comfort": {"name": "Seat cushion retrofit", "owner": "Fleet Planning"},
    "Inflight entertainment": {"name": "Entertainment content refresh", "owner": "Inflight Ops"},
    "On-board service": {"name": "Crew service training", "owner": "Cabin Crew"},
    "Leg room service": {"name": "Economy seat-pitch review", "owner": "Fleet Planning"},
    "Baggage handling": {"name": "Baggage visibility integration", "owner": "Ground Ops"},
    "Checkin service": {"name": "Self check-in expansion", "owner": "Ground Ops"},
    "Inflight service": {"name": "Service recovery playbook", "owner": "Cabin Crew"},
    "Cleanliness": {"name": "Cabin cleaning standards", "owner": "Ground Ops"},
}

# --------------------------------------------------------------- architecture
ARCH_VIEWS = ["Architecture layers", "Zachman matrix", "TOGAF ADM"]
ARCH_LAYERS = [
    ("Business", "Passenger experience management", "Customer Service · Ground Ops · Cabin Crew", "sky"),
    ("Data", "Unified passenger experience model", "Booking · Flight · Feedback · Service ratings", "violet"),
    ("Application", "Analytics and decision support", "Dashboard · CRM · Operations · Reporting", "amber"),
    ("Technology", "Secure integration platform", "Cloud data store · APIs · Identity · Monitoring", "emerald"),
]
ZACHMAN_COLUMNS = ["What · Data", "How · Function", "Where · Network",
                   "Who · People", "When · Time", "Why · Motivation"]
ZACHMAN_ROWS = ["Scope", "Business model", "System model", "Technology model"]
ZACHMAN_CELLS = [
    ["Passenger entities", "Service process", "Channel map", "Stakeholders", "Journey events", "Quality goals"],
    ["Information model", "Business functions", "Operating locations", "Department roles", "Service cycle", "Improvement policy"],
    ["Logical data", "Analytics services", "System integration", "Access model", "Refresh schedule", "KPI rules"],
    ["Data platform", "Applications", "Cloud network", "Identity controls", "Batch pipeline", "Monitoring"],
]
TOGAF_PHASES = ["Preliminary", "Architecture vision", "Business architecture", "Information systems",
                "Technology architecture", "Opportunities & solutions", "Migration planning",
                "Implementation governance"]
