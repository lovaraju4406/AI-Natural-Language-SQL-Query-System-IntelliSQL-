from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os, sqlite3, re, smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
from google import genai

# ── Gemini Client ──────────────────────────────────────────
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODELS = [
    "models/gemini-2.0-flash-lite",
    "models/gemini-2.0-flash-lite-001",
    "models/gemini-2.0-flash-001",
    "models/gemini-2.0-flash",
    "models/gemini-flash-lite-latest",
    "models/gemini-flash-latest",
]

# ── Base SQL Prompt ────────────────────────────────────────
BASE_PROMPT = """
You are an expert SQL assistant. The SQLite database table is named STUDENT with these columns:
  NAME    (text)    — student full name
  CLASS   (text)    — department: CSE, Data Science, AIML, CSE-AIML, CAI
  SECTION (text)    — section: A, B, or C
  GENDER  (text)    — Male or Female
  MARKS   (integer) — score out of 100

Convert the user's question into a valid SQL query.

Examples:
- "How many students?"              → SELECT COUNT(*) FROM STUDENT;
- "All CSE students"                → SELECT * FROM STUDENT WHERE CLASS='CSE';
- "All Data Science students"       → SELECT * FROM STUDENT WHERE CLASS='Data Science';
- "All AIML students"               → SELECT * FROM STUDENT WHERE CLASS='AIML';
- "All CSE-AIML students"           → SELECT * FROM STUDENT WHERE CLASS='CSE-AIML';
- "All CAI students"                → SELECT * FROM STUDENT WHERE CLASS='CAI';
- "Section A students"              → SELECT * FROM STUDENT WHERE SECTION='A';
- "All female students"             → SELECT * FROM STUDENT WHERE GENDER='Female';
- "All male students"               → SELECT * FROM STUDENT WHERE GENDER='Male';
- "Average marks"                   → SELECT ROUND(AVG(MARKS),1) AS AVG_MARKS FROM STUDENT;
- "Highest marks"                   → SELECT * FROM STUDENT WHERE MARKS=(SELECT MAX(MARKS) FROM STUDENT);
- "Students with marks above 80"    → SELECT * FROM STUDENT WHERE MARKS > 80;
- "Class wise average"              → SELECT CLASS, ROUND(AVG(MARKS),1) AS AVG_MARKS FROM STUDENT GROUP BY CLASS ORDER BY AVG_MARKS DESC;
- "Section wise count"              → SELECT CLASS, SECTION, COUNT(*) AS COUNT FROM STUDENT GROUP BY CLASS, SECTION ORDER BY CLASS, SECTION;
- "Gender wise count"               → SELECT GENDER, COUNT(*) AS COUNT FROM STUDENT GROUP BY GENDER;
- "Top 5 students"                  → SELECT * FROM STUDENT ORDER BY MARKS DESC LIMIT 5;
- "Girls in CSE section A"          → SELECT * FROM STUDENT WHERE CLASS='CSE' AND SECTION='A' AND GENDER='Female';
- "Pass count per department"       → SELECT CLASS, COUNT(*) AS PASS FROM STUDENT WHERE MARKS>=40 GROUP BY CLASS;
- "Students between 60 and 80 marks"→ SELECT * FROM STUDENT WHERE MARKS BETWEEN 60 AND 80;
- "Count of students per department"→ SELECT CLASS, COUNT(*) AS TOTAL FROM STUDENT GROUP BY CLASS ORDER BY TOTAL DESC;

STRICT RULES:
- Return ONLY the raw SQL query — no explanation, no ```, no word "sql".
- Never use DROP, DELETE, INSERT, UPDATE, ALTER, CREATE, TRUNCATE.
- Always end the query with a semicolon.
- Use exact values: CLASS values are CSE, Data Science, AIML, CSE-AIML, CAI. GENDER values are Male or Female. SECTION values are A, B, C.
"""

# ════════════════════════════════════════════════════════════
# GLOBAL CSS
# ════════════════════════════════════════════════════════════
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Root Variables ── */
:root {
    --bg-primary: #0A0A14;
    --bg-secondary: #0F0F1E;
    --bg-card: #12122A;
    --bg-card2: #1A1A35;
    --accent: #00E676;
    --accent2: #6C3FC5;
    --accent3: #00BCD4;
    --text-primary: #E0E0F0;
    --text-muted: #888AAA;
    --border: rgba(0, 230, 118, 0.18);
    --border2: rgba(108, 63, 197, 0.3);
    --shadow: 0 4px 32px rgba(0,230,118,0.08);
    --shadow2: 0 2px 16px rgba(108,63,197,0.15);
}

/* ── Base App Styles ── */
.stApp {
    background: var(--bg-primary) !important;
    font-family: 'Rajdhani', sans-serif !important;
    color: var(--text-primary) !important;
}

/* ── SIDEBAR FIX — FORCE ALWAYS VISIBLE ── */

/* Force sidebar open and block collapse button */
[data-testid="stSidebar"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    width: 280px !important;
    min-width: 280px !important;
    max-width: 280px !important;
    transform: none !important;
    position: relative !important;
    background: linear-gradient(180deg, #0D0D20 0%, #0A0A18 100%) !important;
    border-right: 1px solid rgba(0,230,118,0.18) !important;
    overflow: visible !important;
    flex-shrink: 0 !important;
}

[data-testid="stSidebar"] > div:first-child {
    width: 280px !important;
    min-width: 280px !important;
    padding: 0 !important;
}

[data-testid="stSidebarContent"] {
    background: transparent !important;
    padding: 0 0.5rem !important;
    width: 280px !important;
}

/* Hide the collapse/arrow button that hides sidebar */
[data-testid="collapsedControl"],
button[kind="header"],
[data-testid="stSidebarCollapseButton"] {
    display: none !important;
}

/* Ensure main content doesn't take full width */
.main .block-container {
    padding-left: 1rem !important;
    max-width: 100% !important;
}

/* Layout wrapper */
[data-testid="stAppViewContainer"] {
    display: flex !important;
    flex-direction: row !important;
}

[data-testid="stAppViewBlockContainer"] {
    flex: 1 !important;
    min-width: 0 !important;
}

/* ── Sidebar Radio Nav — match reference image ── */
[data-testid="stSidebar"] .stRadio > label {
    /* "Navigation" heading label */
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    color: #E0E0F0 !important;
    letter-spacing: 1px !important;
    margin-bottom: 6px !important;
    display: block !important;
}

[data-testid="stSidebar"] .stRadio > div {
    gap: 2px !important;
    display: flex !important;
    flex-direction: column !important;
}

/* Each radio row */
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] {
    background: transparent !important;
    border: none !important;
    padding: 4px 0 !important;
    margin: 0 !important;
    align-items: center !important;
}

/* Radio circle — keep visible, style like reference */
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {
    display: flex !important;
    margin-right: 10px !important;
}

/* The circle itself */
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] [role="radio"] {
    border-color: #888AAA !important;
    background: transparent !important;
    width: 16px !important;
    height: 16px !important;
}

/* Selected circle — red dot like reference */
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] [aria-checked="true"] [role="radio"],
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] [data-checked="true"] [role="radio"] {
    border-color: #FF4B4B !important;
    background: #FF4B4B !important;
}

/* Label text for each nav item */
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] label,
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] p {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: #C8C8E8 !important;
    cursor: pointer !important;
    transition: color 0.15s !important;
    padding: 2px 0 !important;
    margin: 0 !important;
}

[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover p,
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover label {
    color: #00E676 !important;
}

/* Active/selected label text */
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] [aria-checked="true"] ~ div p,
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] [aria-checked="true"] ~ div label,
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"][aria-checked="true"] p,
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"][aria-checked="true"] label {
    color: #FFFFFF !important;
    font-weight: 700 !important;
}

/* ── Sidebar Logo — match reference ── */
.sidebar-logo {
    padding: 22px 20px 18px;
    border-bottom: 1px solid rgba(0,230,118,0.15);
    margin-bottom: 16px;
}

.sidebar-logo-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
}

.sidebar-logo .logo-icon {
    font-size: 1.7rem;
    line-height: 1;
    flex-shrink: 0;
}

.sidebar-logo .logo-title {
    font-family: 'Segoe UI', 'Rajdhani', sans-serif;
    font-size: 1.45rem;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: 0.5px;
}

.sidebar-logo .logo-title span {
    color: #00E676;
}

.sidebar-logo .logo-sub {
    font-size: 0.82rem;
    color: #888AAA;
    font-family: 'Rajdhani', sans-serif;
    letter-spacing: 0.3px;
    margin-top: 0;
    padding-left: 2px;
}

/* ── Sidebar Stats ── */
.sidebar-stats {
    background: rgba(0,230,118,0.05);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    margin: 8px 0;
    font-family: 'Rajdhani', sans-serif;
}

.sidebar-stats .stat-title {
    color: var(--accent);
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 10px;
    font-family: 'Orbitron', monospace;
}

.sidebar-stats .stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 5px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    color: var(--text-primary);
    font-size: 0.88rem;
}

.sidebar-stats .stat-row:last-child {
    border-bottom: none;
}

.sidebar-stats .stat-val {
    color: var(--accent);
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
}

.sidebar-footer {
    text-align: center;
    padding: 16px 12px 12px;
    color: #888AAA;
    font-size: 0.82rem;
    border-top: 1px solid rgba(0,230,118,0.15);
    margin-top: 12px;
    line-height: 1.8;
    font-family: 'Rajdhani', sans-serif;
}

.sidebar-footer .footer-powered {
    color: #888AAA;
    font-size: 0.78rem;
    letter-spacing: 0.3px;
}

.sidebar-footer .footer-brand {
    color: #FFFFFF;
    font-size: 0.95rem;
    font-weight: 700;
    display: block;
    margin: 2px 0;
}

.sidebar-footer .footer-stack {
    color: #888AAA;
    font-size: 0.78rem;
    display: block;
}

.sidebar-footer .footer-copy {
    color: #555577;
    font-size: 0.75rem;
    display: block;
    margin-top: 6px;
}

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, #0D0D20 0%, #12122A 40%, #0F0F1E 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 40px 36px;
    text-align: center;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}

.hero::before {
    content: '';
    position: absolute;
    top: -40%;
    left: -10%;
    width: 50%;
    height: 200%;
    background: radial-gradient(ellipse, rgba(0,230,118,0.06) 0%, transparent 60%);
    pointer-events: none;
}

.hero::after {
    content: '';
    position: absolute;
    top: -40%;
    right: -10%;
    width: 50%;
    height: 200%;
    background: radial-gradient(ellipse, rgba(108,63,197,0.06) 0%, transparent 60%);
    pointer-events: none;
}

.hero-icon { font-size: 3rem; display: block; margin-bottom: 12px; }

.hero h1 {
    font-family: 'Orbitron', monospace !important;
    font-size: 2.2rem !important;
    font-weight: 900 !important;
    color: var(--accent) !important;
    letter-spacing: 4px !important;
    text-transform: uppercase !important;
    margin: 0 0 10px !important;
    text-shadow: 0 0 30px rgba(0,230,118,0.4) !important;
}

.hero p {
    color: var(--text-muted) !important;
    font-size: 1.05rem !important;
    font-family: 'Rajdhani', sans-serif !important;
    margin-bottom: 16px !important;
}

.hero-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-top: 8px;
}

.badge {
    background: rgba(0,230,118,0.08);
    border: 1px solid rgba(0,230,118,0.25);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.8rem;
    color: var(--accent);
    font-family: 'Rajdhani', sans-serif;
    font-weight: 600;
    letter-spacing: 0.5px;
}

/* ── Section Headers ── */
.section-header {
    font-family: 'Orbitron', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: 3px;
    text-transform: uppercase;
    margin: 20px 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ── Cards ── */
.card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 12px;
    transition: border-color 0.2s, box-shadow 0.2s;
}

.card:hover {
    border-color: rgba(0,230,118,0.35);
    box-shadow: var(--shadow);
}

.card-icon {
    font-size: 1.5rem;
    margin-bottom: 8px;
    display: block;
}

.card h3 {
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    color: var(--accent) !important;
    margin: 0 0 6px !important;
    letter-spacing: 1px !important;
}

.card p {
    color: var(--text-muted) !important;
    font-size: 0.88rem !important;
    margin: 0 !important;
    font-family: 'Rajdhani', sans-serif !important;
    line-height: 1.5 !important;
}

/* ── Metric Cards ── */
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 14px;
    text-align: center;
    transition: all 0.2s;
}

.metric-card:hover {
    border-color: var(--accent);
    box-shadow: 0 0 20px rgba(0,230,118,0.1);
    transform: translateY(-1px);
}

.metric-val {
    font-family: 'Orbitron', monospace;
    font-size: 1.6rem;
    font-weight: 900;
    color: var(--accent);
    display: block;
    line-height: 1.1;
    text-shadow: 0 0 20px rgba(0,230,118,0.3);
}

.metric-label {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.78rem;
    color: var(--text-muted);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-top: 4px;
    display: block;
}

/* ── SQL Display ── */
.sql-box {
    background: #0D1117;
    border: 1px solid rgba(0,230,118,0.2);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    padding: 16px;
    margin: 10px 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.88rem;
    color: #A8D8A8;
    overflow-x: auto;
}

/* ── Info/Insight Boxes ── */
.insight-box {
    background: rgba(108,63,197,0.08);
    border: 1px solid var(--border2);
    border-radius: 10px;
    padding: 16px;
    margin: 10px 0;
    color: var(--text-primary);
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.95rem;
    line-height: 1.7;
}

.insight-title {
    font-family: 'Orbitron', monospace;
    font-size: 0.7rem;
    color: var(--accent2);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 10px;
    font-weight: 700;
}

/* ── Schema Box ── */
.schema-box {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.9rem;
}

.schema-box .schema-title {
    font-family: 'Orbitron', monospace;
    font-size: 0.7rem;
    color: var(--accent);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 12px;
    font-weight: 700;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

.schema-row {
    padding: 5px 0;
    color: var(--text-primary);
    border-bottom: 1px solid rgba(255,255,255,0.04);
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.88rem;
}

/* ── History Items ── */
.history-item {
    background: var(--bg-card);
    border: 1px solid rgba(0,230,118,0.1);
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 8px;
    font-family: 'Rajdhani', sans-serif;
}

.history-time {
    font-size: 0.72rem;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 4px;
}

.history-q {
    color: var(--text-primary);
    font-size: 0.88rem;
    font-weight: 600;
    margin-bottom: 4px;
}

.history-sql {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #A8D8A8;
    background: rgba(0,0,0,0.3);
    padding: 4px 8px;
    border-radius: 4px;
    margin-bottom: 4px;
    overflow-x: auto;
    white-space: nowrap;
}

.history-rows {
    font-size: 0.72rem;
    color: var(--accent);
    font-weight: 700;
}

/* ── Chips ── */
.chips-section {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 16px;
}

.chips-label {
    font-family: 'Orbitron', monospace;
    font-size: 0.68rem;
    color: var(--text-muted);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 10px;
}

/* ── How it works steps ── */
.step-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}

.step-num {
    font-family: 'Orbitron', monospace;
    font-size: 2rem;
    font-weight: 900;
    color: var(--accent);
    display: block;
    margin-bottom: 8px;
    text-shadow: 0 0 20px rgba(0,230,118,0.3);
}

.step-desc {
    color: var(--text-muted);
    font-size: 0.88rem;
    font-family: 'Rajdhani', sans-serif;
    line-height: 1.5;
    white-space: pre-line;
}

/* ── Chat Bubbles ── */
.chat-user {
    background: rgba(108,63,197,0.12);
    border: 1px solid var(--border2);
    border-radius: 12px 12px 4px 12px;
    padding: 12px 16px;
    margin: 8px 0;
    font-family: 'Rajdhani', sans-serif;
    color: var(--text-primary);
    font-size: 0.95rem;
}

.chat-user-label {
    font-size: 0.72rem;
    color: var(--accent2);
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 4px;
    font-family: 'Orbitron', monospace;
}

.chat-bot {
    background: rgba(0,230,118,0.06);
    border: 1px solid var(--border);
    border-radius: 12px 12px 12px 4px;
    padding: 12px 16px;
    margin: 8px 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    color: #C8E6C9;
}

.chat-bot-label {
    font-size: 0.72rem;
    color: var(--accent);
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 4px;
    font-family: 'Orbitron', monospace;
}

/* ── Tip List ── */
.tip-list {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 16px;
}

.tip-item {
    padding: 4px 0;
    color: var(--text-primary);
    font-size: 0.88rem;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-family: 'Rajdhani', sans-serif;
}

.tip-item:last-child { border-bottom: none; }

/* ── Table Overrides ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}

/* ── Button Overrides ── */
.stButton > button {
    background: rgba(0,230,118,0.1) !important;
    border: 1px solid rgba(0,230,118,0.35) !important;
    color: var(--accent) !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    border-radius: 8px !important;
    transition: all 0.2s !important;
}

.stButton > button:hover {
    background: rgba(0,230,118,0.2) !important;
    border-color: var(--accent) !important;
    box-shadow: 0 0 16px rgba(0,230,118,0.2) !important;
}

/* ── Input Overrides ── */
.stTextInput > div > div > input {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    font-family: 'Rajdhani', sans-serif !important;
    border-radius: 8px !important;
}

.stTextInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px rgba(0,230,118,0.3) !important;
}

/* ── Selectbox Overrides ── */
.stSelectbox > div > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 8px !important;
}

/* ── Tab Overrides ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-card) !important;
    border-radius: 8px !important;
    padding: 4px !important;
    border: 1px solid var(--border) !important;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
}

.stTabs [aria-selected="true"] {
    background: rgba(0,230,118,0.12) !important;
    color: var(--accent) !important;
    border-radius: 6px !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
}

/* ── Download Buttons ── */
.stDownloadButton > button {
    background: rgba(0,188,212,0.1) !important;
    border: 1px solid rgba(0,188,212,0.35) !important;
    color: var(--accent3) !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}

/* ── Alerts ── */
.stSuccess, .stError, .stWarning, .stInfo {
    border-radius: 8px !important;
    font-family: 'Rajdhani', sans-serif !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); }
::-webkit-scrollbar-thumb { background: rgba(0,230,118,0.3); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0,230,118,0.5); }

/* ── Hide Streamlit Branding ── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

/* ── Tech Stack Cards ── */
.tech-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px;
    transition: all 0.2s;
    height: 100%;
}

.tech-card:hover {
    border-color: rgba(0,230,118,0.4);
    box-shadow: var(--shadow);
    transform: translateY(-2px);
}

.tech-icon { font-size: 1.8rem; display: block; margin-bottom: 8px; }
.tech-name {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: var(--accent);
    margin: 0 0 6px;
}
.tech-desc {
    color: var(--text-muted);
    font-size: 0.84rem;
    font-family: 'Rajdhani', sans-serif;
    line-height: 1.5;
}

/* ── Export Section ── */
.export-box {
    background: rgba(0,188,212,0.05);
    border: 1px solid rgba(0,188,212,0.2);
    border-radius: 10px;
    padding: 14px 16px;
    margin: 10px 0;
}

.export-title {
    font-family: 'Orbitron', monospace;
    font-size: 0.68rem;
    color: var(--accent3);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 10px;
    font-weight: 700;
}

/* ── Results Box ── */
.results-header {
    background: rgba(0,230,118,0.05);
    border: 1px solid var(--border);
    border-radius: 10px 10px 0 0;
    padding: 10px 16px;
    font-family: 'Orbitron', monospace;
    font-size: 0.68rem;
    color: var(--accent);
    letter-spacing: 2px;
    text-transform: uppercase;
    font-weight: 700;
}
</style>
"""

# ════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════
@st.cache_data(ttl=30)
def db_stats():
    try:
        conn = sqlite3.connect("student.db")
        c = conn.cursor()
        total   = c.execute("SELECT COUNT(*) FROM STUDENT").fetchone()[0]
        avg_m   = c.execute("SELECT ROUND(AVG(MARKS),1) FROM STUDENT").fetchone()[0]
        top_m   = c.execute("SELECT MAX(MARKS) FROM STUDENT").fetchone()[0]
        classes = c.execute("SELECT COUNT(DISTINCT CLASS) FROM STUDENT").fetchone()[0]
        pass_r  = c.execute("SELECT COUNT(*) FROM STUDENT WHERE MARKS >= 40").fetchone()[0]
        conn.close()
        return total, avg_m, top_m, classes, round(pass_r/total*100,1) if total else 0
    except:
        return 0, 0, 0, 0, 0

@st.cache_data(ttl=60)
def load_all_students():
    try:
        conn = sqlite3.connect("student.db")
        df = pd.read_sql_query("SELECT * FROM STUDENT", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame()

def gemini(prompt_text, max_retries=2):
    for m in MODELS:
        for _ in range(max_retries):
            try:
                r = client.models.generate_content(model=m, contents=prompt_text)
                return r.text.strip()
            except Exception:
                continue
    raise Exception("AI models temporarily unavailable. Try again.")

def run_sql(sql, db="student.db"):
    conn = sqlite3.connect(db)
    cur  = conn.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return rows, cols

def is_safe_sql(sql):
    danger = r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE)\b"
    return not bool(re.search(danger, sql, re.IGNORECASE))

def nl_to_sql(question):
    return gemini(BASE_PROMPT + f"\n\nQuestion: {question}\nSQL:")

def explain_sql(sql):
    return gemini(f"""Explain this SQL query in simple plain English for a non-technical person.
Be concise — 2 to 3 sentences only. Focus on what data it retrieves.
SQL: {sql}""")

def optimize_sql(sql):
    return gemini(f"""Review this SQL query and suggest an improved version if possible.
Explain the improvement in 1-2 sentences. If the query is already optimal, say so.
SQL: {sql}""")

def ai_insights(df):
    sample = df.head(30).to_string(index=False)
    return gemini(f"""Analyze this student data and provide exactly 5 concise bullet-point insights.
Focus on patterns, top/bottom performers, class comparisons, and notable trends.
Format each point starting with a relevant emoji.
Data:
{sample}""")

def translate_to_english(text):
    return gemini(f"Translate this to English. Return ONLY the English translation, nothing else:\n{text}")

def is_english(text):
    r = gemini(f"Is this text written in English? Reply with only YES or NO:\n{text}")
    return "YES" in r.upper()

def auto_sample_questions(cols_info):
    return gemini(f"""Generate exactly 8 useful natural language questions a user can ask about a database table with these columns: {cols_info}
Number them 1-8. Make them varied — include filters, aggregations, comparisons, and rankings.""")

def make_html_report(question, sql, df, explanation=""):
    th = "".join(f"<th>{c}</th>" for c in df.columns)
    tr = "".join("<tr>"+"".join(f"<td>{v}</td>" for v in r)+"</tr>" for _,r in df.iterrows())
    ex = f"<div class='section'><h3>💡 Explanation</h3><p>{explanation}</p></div>" if explanation else ""
    return f"""<!DOCTYPE html><html><head><title>IntelliSQL Report</title>
<style>body{{font-family:monospace;background:#0A0A14;color:#E0E0F0;padding:40px;}}
h1{{color:#00E676;}} h3{{color:#00BCD4;}} pre{{background:#12122A;padding:16px;border-radius:8px;color:#A8D8A8;}}
table{{width:100%;border-collapse:collapse;margin-top:16px;}}
th{{background:#12122A;color:#00E676;padding:10px;text-align:left;border:1px solid rgba(0,230,118,0.2);}}
td{{padding:8px 10px;border:1px solid rgba(255,255,255,0.05);}}
tr:nth-child(even){{background:rgba(255,255,255,0.03);}}
.section{{background:#12122A;border:1px solid rgba(0,230,118,0.2);border-radius:8px;padding:20px;margin:16px 0;}}
.badge{{background:rgba(0,230,118,0.1);border:1px solid rgba(0,230,118,0.3);padding:3px 12px;border-radius:20px;font-size:0.8rem;color:#00E676;display:inline-block;margin:4px;}}
footer{{margin-top:40px;color:#888;font-size:0.8rem;text-align:center;}}
</style></head><body>
<h1>🗄️ IntelliSQL Query Report</h1>
<p style="color:#888">{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<div class="section"><h3>❓ Question</h3><p>{question}</p></div>
<div class="section"><h3>🧾 Generated SQL</h3><pre>{sql}</pre></div>
{ex}
<div class="section"><h3>📊 Results <span style="color:#888;font-size:0.85rem">— {len(df)} rows</span></h3>
<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>
<footer>Generated by IntelliSQL — Powered by Google Gemini AI</footer>
</body></html>""".encode()

def send_email(to, subject, body, user, pwd):
    msg = MIMEMultipart()
    msg["From"] = user; msg["To"] = to; msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pwd); s.send_message(msg)

def render_chart(df, prefix=""):
    numeric = df.select_dtypes(include="number").columns.tolist()
    if not numeric:
        return
    st.markdown('<div class="section-header">📈 Visualization</div>', unsafe_allow_html=True)
    o1, o2, o3 = st.columns(3)
    with o1: ctype = st.selectbox("Type", ["Bar","Line","Pie","Area","Scatter"], key=f"{prefix}ct")
    with o2: y = st.selectbox("Value (Y)", numeric, key=f"{prefix}y")
    with o3: x = st.selectbox("Label (X)", df.columns.tolist(), key=f"{prefix}x")
    try:
        import plotly.express as px
        kw = dict(template="plotly_dark", color_discrete_sequence=["#00E676","#00C853","#6C3FC5","#0F3460","#E91E63"])
        gl = dict(plot_bgcolor="#12122A", paper_bgcolor="#12122A", font_color="#E0E0E0",
                  title_font_color="#00E676", title_font_size=15, margin=dict(l=20,r=20,t=40,b=20))
        str_c = df.select_dtypes(include="object").columns.tolist()
        color = str_c[0] if str_c and ctype not in ["Pie"] else None
        if   ctype == "Bar":     fig = px.bar(df,x=x,y=y,color=color,**kw,title=f"{y} by {x}")
        elif ctype == "Line":    fig = px.line(df,x=x,y=y,color=color,**kw,title=f"{y} over {x}")
        elif ctype == "Pie":     fig = px.pie(df,names=x,values=y,**kw,title=f"{y} split")
        elif ctype == "Area":    fig = px.area(df,x=x,y=y,color=color,**kw,title=f"{y} area")
        elif ctype == "Scatter": fig = px.scatter(df,x=x,y=y,color=color,**kw,title=f"{y} vs {x}",size_max=14)
        fig.update_layout(**gl)
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        if ctype in ["Bar"]: st.bar_chart(df.set_index(x)[y])
        else:                st.line_chart(df.set_index(x)[y])
        st.caption("Install plotly for richer charts: `pip install plotly`")

def init_state():
    defaults = {"history":[], "chat":[], "chip_q":"", "last_sql":"", "last_df":None}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def metric_card(val, label):
    return f'<div class="metric-card"><span class="metric-val">{val}</span><span class="metric-label">{label}</span></div>'

# ════════════════════════════════════════════════════════════
# PAGE: HOME
# ════════════════════════════════════════════════════════════
def page_home():
    st.markdown(CSS, unsafe_allow_html=True)

    # Hero
    st.markdown("""
<div class="hero">
  <span class="hero-icon">🗄️</span>
  <h1>IntelliSQL</h1>
  <p>Ask questions in plain English — get instant SQL results, charts &amp; AI insights</p>
  <div class="hero-badges">
    <span class="badge">🤖 Gemini AI</span>
    <span class="badge">🐍 Python</span>
    <span class="badge">🗄️ SQLite</span>
    <span class="badge">🌐 Streamlit</span>
    <span class="badge">📊 Plotly</span>
    <span class="badge">🌍 Multi-lang</span>
    <span class="badge">🛡️ SQL Guard</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # Live stats
    total, avg_m, top_m, cls, pass_r = db_stats()
    st.markdown('<div class="section-header">📊 Live Stats</div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5)
    for col, v, l in zip([c1,c2,c3,c4,c5],
                         [total, avg_m, top_m, cls, f"{pass_r}%"],
                         ["Students","Avg Marks","Top Score","Classes","Pass Rate"]):
        with col: st.markdown(metric_card(v,l), unsafe_allow_html=True)

    # Features
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">✨ Features</div>', unsafe_allow_html=True)
    feats = [
        ("🔍","Smart Query","Type any question in plain English and get accurate SQL results instantly."),
        ("📊","Dashboard","6 auto-generated charts — class stats, distributions, top performers."),
        ("💬","AI Chatbot","Multi-turn conversation with memory for follow-up questions."),
        ("🌍","Multi-language","Ask in Hindi, Telugu, Tamil, French — auto-translated to SQL."),
        ("🧠","AI Insights","Automatic bullet-point data analysis after every query result."),
        ("⚡","SQL Optimizer","AI suggests a faster, better version of every generated query."),
        ("🛡️","Safety Guard","Blocks DROP/DELETE/INSERT before execution automatically."),
        ("📝","Auto Questions","AI generates sample questions from any uploaded database schema."),
        ("📋","History","Full log of every query with timestamps and row counts."),
        ("⬇️","CSV & Report","One-click CSV export and downloadable HTML query reports."),
        ("📁","Upload DB/CSV","Query any SQLite or CSV file with natural language."),
        ("➕","Manage Data","Add or delete student records directly from the UI."),
    ]
    cols = st.columns(3)
    for i,(icon,title,desc) in enumerate(feats):
        with cols[i%3]:
            st.markdown(f'<div class="card"><span class="card-icon">{icon}</span><h3>{title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)

    # How it works
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">⚙️ How It Works</div>', unsafe_allow_html=True)
    steps = [("1","Type your question\nin any language"),("2","Gemini AI converts\nit to safe SQL"),
             ("3","SQL runs on your\nSQLite database"),("4","See results, charts\n& AI insights")]
    for col,(n,d) in zip(st.columns(4),steps):
        with col:
            st.markdown(f'<div class="step-card"><span class="step-num">{n}</span><span class="step-desc">{d}</span></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: QUERY
# ════════════════════════════════════════════════════════════
def page_query():
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()

    st.markdown("""
<div class="hero">
  <span class="hero-icon">🔍</span>
  <h1>Query Assistant</h1>
  <p>Ask in any language — get SQL, insights, charts &amp; exports</p>
</div>
""", unsafe_allow_html=True)

    # Chips
    chips = [
        "How many students?","All CSE students","Highest marks?",
        "Average marks?","All AIML students","Section A students",
        "All female students","All male students","CSE-AIML students",
        "Top 5 students","CAI students","Class-wise average marks",
        "Marks above 80?","Marks below 50?","Gender-wise count",
        "Section wise count","Data Science students","Pass count by class",
    ]
    st.markdown('<div class="section-header">🧩 Quick Queries</div>', unsafe_allow_html=True)
    rows_of_chips = [chips[:6], chips[6:12], chips[12:18]]
    for row_i, row in enumerate(rows_of_chips):
        chip_cols = st.columns(6)
        for ci, (chip_col, chip) in enumerate(zip(chip_cols, row)):
            with chip_col:
                if st.button(chip, key=f"chip_{row_i}_{ci}"):
                    st.session_state.chip_q = chip

    st.markdown("<br>", unsafe_allow_html=True)
    main_col, side_col = st.columns([5,2])

    with main_col:
        question = st.text_input(
            "Your question",
            value=st.session_state.chip_q,
            placeholder="e.g. Show all students with marks above 75 in Data Science",
            key="q_in"
        )
        go = st.button("⚡ Generate & Run", key="go_btn")

        if go:
            st.session_state.chip_q = ""
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("🌍 Processing..."):
                    try:
                        if not is_english(question):
                            translated = translate_to_english(question)
                            st.info(f"🌍 Translated: **{translated}**")
                            q_eng = translated
                        else:
                            q_eng = question
                    except:
                        q_eng = question

                with st.spinner("🤖 Generating SQL..."):
                    try:
                        sql = nl_to_sql(q_eng)
                        sql = re.sub(r"```sql|```","", sql).strip()
                        if not sql.endswith(";"): sql += ";"
                    except Exception as e:
                        st.error(f"❌ AI Error: {e}")
                        sql = None

                if sql:
                    if not is_safe_sql(sql):
                        st.error("🛡️ **Blocked!** Dangerous SQL operation detected (DROP/DELETE/INSERT/UPDATE). Query rejected for safety.")
                    else:
                        st.session_state.last_sql = sql
                        st.markdown('<div class="section-header">🧾 Generated SQL</div>', unsafe_allow_html=True)
                        st.code(sql, language="sql")

                        tab1, tab2, tab3 = st.tabs(["💡 Explain", "⚡ Optimize", "🧠 Insights"])

                        with tab1:
                            with st.spinner("Explaining..."):
                                expl = explain_sql(sql)
                            st.markdown(f'<div class="insight-box"><div class="insight-title">What this query does</div>{expl}</div>', unsafe_allow_html=True)

                        with st.spinner("🗄️ Fetching results..."):
                            try:
                                rows, col_names = run_sql(sql)
                            except Exception as e:
                                st.error(f"❌ DB Error: {e}")
                                rows = None

                        if rows is not None:
                            if rows:
                                df = pd.DataFrame(rows, columns=col_names)
                                st.session_state.last_df = df

                                st.markdown('<div class="section-header">📊 Results</div>', unsafe_allow_html=True)
                                mc1, mc2, mc3 = st.columns(3)
                                with mc1: st.markdown(metric_card(len(df),"Rows Found"), unsafe_allow_html=True)
                                with mc2: st.markdown(metric_card(len(df.columns),"Columns"), unsafe_allow_html=True)
                                with mc3:
                                    num = df.select_dtypes(include="number")
                                    v = round(num.iloc[:,0].mean(),1) if not num.empty else "—"
                                    l = f"Avg {num.columns[0]}" if not num.empty else "Result"
                                    st.markdown(metric_card(v,l), unsafe_allow_html=True)

                                st.markdown("<br>", unsafe_allow_html=True)
                                st.dataframe(df, use_container_width=True, hide_index=True)

                                with tab3:
                                    with st.spinner("Analyzing data..."):
                                        ins = ai_insights(df)
                                    st.markdown(f'<div class="insight-box"><div class="insight-title">AI Data Insights</div>{ins}</div>', unsafe_allow_html=True)

                                with tab2:
                                    with st.spinner("Optimizing..."):
                                        opt = optimize_sql(sql)
                                    st.markdown(f'<div class="insight-box"><div class="insight-title">Optimization Suggestion</div>{opt}</div>', unsafe_allow_html=True)

                                # Export
                                st.markdown('<div class="export-box"><div class="export-title">⬇️ Export</div>', unsafe_allow_html=True)
                                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                                ex1, ex2 = st.columns(2)
                                with ex1:
                                    st.download_button("📥 Download CSV", df.to_csv(index=False).encode(), f"results_{ts}.csv","text/csv")
                                with ex2:
                                    st.download_button("📄 HTML Report", make_html_report(question,sql,df,expl), f"report_{ts}.html","text/html")
                                st.markdown('</div>', unsafe_allow_html=True)

                                # Email
                                with st.expander("📧 Email Results"):
                                    em1,em2,em3 = st.columns(3)
                                    with em1: to_a = st.text_input("Recipient Email", key="eto")
                                    with em2: su   = st.text_input("Your Gmail",      key="esu")
                                    with em3: sp   = st.text_input("App Password", type="password", key="esp")
                                    if st.button("📨 Send", key="send_em"):
                                        body = f"<h2>IntelliSQL Results</h2><p>Question: {question}</p><pre>{sql}</pre>{df.to_html(index=False)}"
                                        try:
                                            send_email(to_a, f"IntelliSQL: {question[:50]}", body, su, sp)
                                            st.success("✅ Email sent!")
                                        except Exception as ex:
                                            st.error(f"❌ {ex}")

                                render_chart(df, "q_")
                                st.session_state.history.insert(0,{
                                    "time": datetime.now().strftime("%H:%M:%S"),
                                    "question": question,
                                    "sql": sql,
                                    "rows": len(df)
                                })
                                st.success(f"✅ {len(df)} record(s) found.")
                            else:
                                st.info("ℹ️ No records matched your query.")

    with side_col:
        st.markdown('<div class="section-header">🗃️ Schema</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="schema-box">
  <div class="schema-title">STUDENT Table</div>
  <div class="schema-row">🟢 <b>NAME</b> — Student name</div>
  <div class="schema-row">🟢 <b>CLASS</b> — CSE / Data Science / AIML / CSE-AIML / CAI</div>
  <div class="schema-row">🟢 <b>SECTION</b> — A, B or C</div>
  <div class="schema-row">🟢 <b>GENDER</b> — Male or Female</div>
  <div class="schema-row">🟢 <b>MARKS</b> — Score out of 100</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">💡 Try Asking</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="tip-list">
  <div class="tip-item">📌 Top 5 students by marks</div>
  <div class="tip-item">📌 Class-wise average marks</div>
  <div class="tip-item">📌 All female CSE students</div>
  <div class="tip-item">📌 CSE section A students</div>
  <div class="tip-item">📌 Students between 60-80</div>
  <div class="tip-item">📌 Gender-wise count</div>
  <div class="tip-item">📌 Pass count per department</div>
  <div class="tip-item">📌 Section wise student count</div>
  <div class="tip-item">🇮🇳 सबसे ज्यादा marks किसके?</div>
  <div class="tip-item">🇮🇳 CSE విద్యార్థులు చూపించు</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">🕓 History</div>', unsafe_allow_html=True)
        if st.session_state.history:
            if st.button("🗑️ Clear History"):
                st.session_state.history = []; st.rerun()
            for h in st.session_state.history[:5]:
                st.markdown(f"""
<div class="history-item">
  <div class="history-time">⏱ {h["time"]}</div>
  <div class="history-q">{h["question"]}</div>
  <div class="history-sql">{h["sql"]}</div>
  <div class="history-rows">{h["rows"]} rows</div>
</div>
""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="insight-box" style="text-align:center;color:#888;">No queries yet</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ════════════════════════════════════════════════════════════
def page_dashboard():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("""
<div class="hero">
  <span class="hero-icon">📊</span>
  <h1>Dashboard</h1>
  <p>Real-time analytics and visual insights from your student database</p>
</div>
""", unsafe_allow_html=True)

    df = load_all_students()
    if df.empty:
        st.error("❌ Could not load student.db — run sql.py first.")
        return

    total = len(df); avg_m = round(df["MARKS"].mean(),1)
    top_m = df["MARKS"].max(); low_m = df["MARKS"].min()
    pass_r = round(len(df[df["MARKS"]>=40])/total*100,1)

    c1,c2,c3,c4,c5 = st.columns(5)
    for col,v,l in zip([c1,c2,c3,c4,c5],
                       [total,avg_m,top_m,low_m,f"{pass_r}%"],
                       ["Students","Avg Marks","Highest","Lowest","Pass Rate"]):
        with col: st.markdown(metric_card(v,l), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    try:
        import plotly.express as px
        kw = dict(template="plotly_dark", color_discrete_sequence=["#00E676","#00C853","#6C3FC5","#0F3460","#E91E63","#FF6D00"])
        bg = dict(plot_bgcolor="#12122A", paper_bgcolor="#12122A", font_color="#E0E0E0",
                  title_font_color="#00E676", margin=dict(l=20,r=20,t=40,b=20))

        r1, r2 = st.columns(2)
        with r1:
            st.markdown('<div class="section-header">📚 Class Average Marks</div>', unsafe_allow_html=True)
            ca = df.groupby("CLASS")["MARKS"].mean().reset_index().rename(columns={"MARKS":"AVG"})
            ca["AVG"] = ca["AVG"].round(1)
            fig = px.bar(ca, x="CLASS", y="AVG", color="CLASS", **kw, text="AVG", title="Average Marks by Class")
            fig.update_traces(textposition="outside"); fig.update_layout(**bg)
            st.plotly_chart(fig, use_container_width=True)
        with r2:
            st.markdown('<div class="section-header">👥 Gender Distribution</div>', unsafe_allow_html=True)
            sc = df["GENDER"].value_counts().reset_index(); sc.columns=["Gender","Count"]
            fig2 = px.pie(sc, names="Gender", values="Count", **kw, title="Male vs Female Students",
                          hole=0.45, color_discrete_map={"Male":"#00E676","Female":"#6C3FC5"})
            fig2.update_layout(**bg); fig2.update_traces(textinfo="label+percent")
            st.plotly_chart(fig2, use_container_width=True)

        r2a, r2b = st.columns(2)
        with r2a:
            st.markdown('<div class="section-header">📈 Marks Distribution</div>', unsafe_allow_html=True)
            fig3 = px.histogram(df, x="MARKS", nbins=10, color_discrete_sequence=["#00E676"],
                                template="plotly_dark", title="Frequency of Marks", labels={"MARKS":"Marks"})
            fig3.update_layout(**bg); st.plotly_chart(fig3, use_container_width=True)
        with r2b:
            st.markdown('<div class="section-header">🏆 Top 8 Students</div>', unsafe_allow_html=True)
            t8 = df.nlargest(8,"MARKS")
            fig4 = px.bar(t8, x="NAME", y="MARKS", color="CLASS", **kw, title="Top 8 Students")
            fig4.update_layout(**bg); st.plotly_chart(fig4, use_container_width=True)

        r3a, r3b = st.columns(2)
        with r3a:
            st.markdown('<div class="section-header">✅ Pass vs Fail by Class</div>', unsafe_allow_html=True)
            df2 = df.copy(); df2["Status"] = df2["MARKS"].apply(lambda x:"Pass ✅" if x>=40 else "Fail ❌")
            pf = df2.groupby(["CLASS","Status"])["NAME"].count().reset_index()
            pf.columns=["CLASS","Status","Count"]
            fig5 = px.bar(pf, x="CLASS", y="Count", color="Status", barmode="group",
                          template="plotly_dark",
                          color_discrete_map={"Pass ✅":"#00E676","Fail ❌":"#E91E63"},
                          title="Pass vs Fail per Class")
            fig5.update_layout(**bg); st.plotly_chart(fig5, use_container_width=True)
        with r3b:
            st.markdown('<div class="section-header">🔥 Marks Heatmap</div>', unsafe_allow_html=True)
            hm = df.groupby(["CLASS","SECTION"])["MARKS"].mean().reset_index()
            hp = hm.pivot(index="CLASS",columns="SECTION",values="MARKS").fillna(0).round(1)
            fig6 = px.imshow(hp, color_continuous_scale="Greens", template="plotly_dark",
                             title="Avg Marks — Class × Section", text_auto=True)
            fig6.update_layout(**bg); st.plotly_chart(fig6, use_container_width=True)
    except ImportError:
        st.warning("Install plotly for charts: `pip install plotly`")

    st.markdown('<div class="section-header">📋 Full Records</div>', unsafe_allow_html=True)
    st.dataframe(df.sort_values("MARKS",ascending=False), use_container_width=True, hide_index=True)
    st.download_button("📥 Download All CSV", df.to_csv(index=False).encode(), "students.csv","text/csv")

# ════════════════════════════════════════════════════════════
# PAGE: CHATBOT
# ════════════════════════════════════════════════════════════
def page_chatbot():
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()

    st.markdown("""
<div class="hero">
  <span class="hero-icon">💬</span>
  <h1>AI Chatbot</h1>
  <p>Multi-turn SQL conversation — ask follow-up questions with full memory</p>
</div>
""", unsafe_allow_html=True)

    if st.button("🗑️ New Chat"):
        st.session_state.chat = []; st.rerun()

    for msg in st.session_state.chat:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user"><div class="chat-user-label">👤 You</div>{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-bot"><div class="chat-bot-label">🤖 IntelliSQL</div>{msg["content"]}</div>', unsafe_allow_html=True)
            if msg.get("df") is not None:
                st.dataframe(msg["df"], use_container_width=True, hide_index=True)

    user_input = st.chat_input("Ask about the student database... (e.g. 'Now filter only section A')")
    if user_input:
        st.session_state.chat.append({"role":"user","content":user_input})
        ctx = "\n".join(
            f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
            for m in st.session_state.chat[-8:]
        )
        chat_prompt = f"""{BASE_PROMPT}

CONVERSATION HISTORY (for context):
{ctx}

IMPORTANT: Use the conversation history to understand follow-up questions.
If user says "now only section A" or "filter by class", modify the previous SQL accordingly.
Return ONLY the raw SQL query for the latest user message."""

        with st.spinner("🤖 Thinking..."):
            try:
                sql = gemini(chat_prompt)
                sql = re.sub(r"```sql|```","",sql).strip()
                if not sql.endswith(";"): sql += ";"
                if not is_safe_sql(sql):
                    reply = "🛡️ Blocked: Dangerous SQL operation detected."
                    st.session_state.chat.append({"role":"assistant","content":reply,"df":None})
                else:
                    rows, cols = run_sql(sql)
                    df = pd.DataFrame(rows, columns=cols) if rows else None
                    result_text = f"**SQL:** `{sql}`\n\n{'**' + str(len(df)) + ' result(s) found.**' if df is not None and not df.empty else 'No results found.'}"
                    st.session_state.chat.append({"role":"assistant","content":result_text,"df":df})
            except Exception as e:
                st.session_state.chat.append({"role":"assistant","content":f"❌ {e}","df":None})
        st.rerun()

# ════════════════════════════════════════════════════════════
# PAGE: MANAGE
# ════════════════════════════════════════════════════════════
def page_manage():
    st.markdown(CSS, unsafe_allow_html=True)

    st.markdown("""
<div class="hero">
  <span class="hero-icon">➕</span>
  <h1>Manage Data</h1>
  <p>Add new students or remove existing records from the database</p>
</div>
""", unsafe_allow_html=True)

    add_col, del_col = st.columns(2)

    with add_col:
        st.markdown('<div class="section-header">➕ Add Student</div>', unsafe_allow_html=True)
        with st.form("add_f", clear_on_submit=True):
            name  = st.text_input("Full Name")
            cls   = st.selectbox("Department", ["CSE","Data Science","AIML","CSE-AIML","CAI","Other"])
            cls_c = st.text_input("Custom department name (if Other)")
            sec   = st.selectbox("Section", ["A","B","C"])
            gen   = st.selectbox("Gender", ["Male","Female"])
            mrk   = st.number_input("Marks (0–100)", 0, 100, 75)
            if st.form_submit_button("✅ Add Student"):
                fc = cls_c.strip() if cls=="Other" and cls_c.strip() else cls
                if not name.strip():
                    st.error("❌ Name is required.")
                else:
                    try:
                        conn = sqlite3.connect("student.db")
                        conn.cursor().execute("INSERT INTO STUDENT VALUES(?,?,?,?,?)",(name.strip(),fc,sec,gen,int(mrk)))
                        conn.commit(); conn.close()
                        st.success(f"✅ '{name}' added to {fc} — Section {sec} — {gen} — {mrk} marks!")
                        st.cache_data.clear(); st.rerun()
                    except Exception as e:
                        st.error(f"❌ {e}")

    with del_col:
        st.markdown('<div class="section-header">🗑️ Delete Student</div>', unsafe_allow_html=True)
        try:
            conn   = sqlite3.connect("student.db")
            df_all = pd.read_sql_query("SELECT rowid,* FROM STUDENT ORDER BY NAME", conn); conn.close()
            if df_all.empty:
                st.info("No students in database.")
            else:
                opts = {f"{r['NAME']} | {r['CLASS']} | Sec {r['SECTION']} | {r['MARKS']} marks": r["rowid"]
                        for _,r in df_all.iterrows()}
                sel = st.selectbox("Select student:", list(opts.keys()))
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Delete Selected Student"):
                    conn = sqlite3.connect("student.db")
                    conn.cursor().execute("DELETE FROM STUDENT WHERE rowid=?",(opts[sel],))
                    conn.commit(); conn.close()
                    st.success("✅ Deleted successfully!")
                    st.cache_data.clear(); st.rerun()
        except Exception as e:
            st.error(f"❌ {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">📋 All Records</div>', unsafe_allow_html=True)
    try:
        df_s = load_all_students()
        c1,c2,c3,c4 = st.columns(4)
        for col,v,l in zip([c1,c2,c3,c4],
                           [len(df_s),
                            round(df_s["MARKS"].mean(),1) if not df_s.empty else 0,
                            df_s["MARKS"].max() if not df_s.empty else 0,
                            df_s["CLASS"].nunique() if not df_s.empty else 0],
                           ["Total","Avg Marks","Highest","Classes"]):
            with col: st.markdown(metric_card(v,l), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(df_s.sort_values("MARKS",ascending=False), use_container_width=True, hide_index=True)
        st.download_button("📥 Export CSV", df_s.to_csv(index=False).encode(),"students.csv","text/csv")
    except Exception as e:
        st.error(f"❌ {e}")

# ════════════════════════════════════════════════════════════
# PAGE: UPLOAD
# ════════════════════════════════════════════════════════════
def page_upload():
    st.markdown(CSS, unsafe_allow_html=True)

    st.markdown("""
<div class="hero">
  <span class="hero-icon">📁</span>
  <h1>Upload &amp; Query</h1>
  <p>Upload any SQLite .db or CSV file and query it with natural language</p>
</div>
""", unsafe_allow_html=True)

    utype = st.radio("Choose file type:", ["📊 CSV File","🗄️ SQLite .db File"], horizontal=True)

    if utype == "📊 CSV File":
        up = st.file_uploader("Upload CSV", type=["csv"])
        if up:
            df_c = pd.read_csv(up)
            c1,c2,c3 = st.columns(3)
            with c1: st.markdown(metric_card(len(df_c),"Rows"), unsafe_allow_html=True)
            with c2: st.markdown(metric_card(len(df_c.columns),"Columns"), unsafe_allow_html=True)
            with c3: st.markdown(metric_card(df_c.select_dtypes(include="number").columns.__len__(),"Numeric Cols"), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.dataframe(df_c.head(8), use_container_width=True, hide_index=True)

            with st.expander("📝 AI-Generated Sample Questions"):
                with st.spinner("Generating questions from schema..."):
                    qs = auto_sample_questions(", ".join(df_c.columns.tolist()))
                st.markdown(f'<div class="insight-box">{qs}</div>', unsafe_allow_html=True)

            tmp = "/tmp/csv_upload.db"
            ct  = sqlite3.connect(tmp); df_c.to_sql("my_table",ct,if_exists="replace",index=False); ct.close()
            cp  = f"Table: my_table. Columns: {', '.join(df_c.columns)}. Return ONLY raw SQL. No ``` or sql word."

            q_c = st.text_input("Ask about your CSV:", placeholder="e.g. Show rows where...", key="csvq")
            if st.button("⚡ Query CSV") and q_c.strip():
                with st.spinner("Generating SQL..."):
                    try:
                        sql = gemini(cp + f"\nQuestion: {q_c}")
                        sql = re.sub(r"```sql|```","",sql).strip()
                        st.code(sql, language="sql")
                        rows, cols = run_sql(sql, tmp)
                        if rows:
                            r_df = pd.DataFrame(rows, columns=cols)
                            st.dataframe(r_df, use_container_width=True, hide_index=True)
                            st.download_button("📥 Download Result", r_df.to_csv(index=False).encode(),"result.csv","text/csv")
                            render_chart(r_df, "csv_")
                        else:
                            st.info("No results.")
                    except Exception as e:
                        st.error(f"❌ {e}")
    else:
        up_db = st.file_uploader("Upload .db file", type=["db"])
        if up_db:
            tmp_db = f"/tmp/{up_db.name}"
            with open(tmp_db,"wb") as f: f.write(up_db.read())
            try:
                conn   = sqlite3.connect(tmp_db)
                tables = [t[0] for t in conn.cursor().execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                conn.close()
                st.success(f"✅ {len(tables)} table(s) found: {', '.join(tables)}")
                tbl  = st.selectbox("Choose table:", tables)
                conn = sqlite3.connect(tmp_db)
                df_p = pd.read_sql_query(f"SELECT * FROM '{tbl}' LIMIT 8", conn); conn.close()
                st.dataframe(df_p, use_container_width=True, hide_index=True)

                with st.expander("📝 AI-Generated Sample Questions"):
                    with st.spinner("Generating..."):
                        qs2 = auto_sample_questions(f"table '{tbl}' with columns: {', '.join(df_p.columns.tolist())}")
                    st.markdown(f'<div class="insight-box">{qs2}</div>', unsafe_allow_html=True)

                dp  = f"Table: {tbl}. Columns: {', '.join(df_p.columns)}. Return ONLY raw SQL. No ``` or sql word."
                q_d = st.text_input("Ask about your database:", key="dbq")
                if st.button("⚡ Query DB") and q_d.strip():
                    with st.spinner("Generating SQL..."):
                        try:
                            sql = gemini(dp + f"\nQuestion: {q_d}")
                            sql = re.sub(r"```sql|```","",sql).strip()
                            st.code(sql, language="sql")
                            rows, c_n = run_sql(sql, tmp_db)
                            if rows:
                                r_df = pd.DataFrame(rows, columns=c_n)
                                st.dataframe(r_df, use_container_width=True, hide_index=True)
                                st.download_button("📥 Download", r_df.to_csv(index=False).encode(),"result.csv","text/csv")
                                render_chart(r_df,"db_")
                            else:
                                st.info("No results.")
                        except Exception as e:
                            st.error(f"❌ {e}")
            except Exception as e:
                st.error(f"❌ {e}")

# ════════════════════════════════════════════════════════════
# PAGE: ABOUT
# ════════════════════════════════════════════════════════════
def page_about():
    st.markdown(CSS, unsafe_allow_html=True)

    st.markdown("""
<div class="hero">
  <span class="hero-icon">ℹ️</span>
  <h1>About</h1>
  <p>Technology stack, architecture and database schema</p>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="section-header">🎯 What is IntelliSQL?</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="insight-box">
IntelliSQL is a production-grade AI-powered Natural Language to SQL platform. It uses Google Gemini to convert
plain English questions (in any language) into precise SQL queries, executes them on SQLite, and returns results
with charts, AI insights, and export options. Built for students, teachers, and data analysts who want to explore
databases without writing a single line of SQL.
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="section-header">🛠️ Tech Stack</div>', unsafe_allow_html=True)
    tech = [
        ("🤖","Google Gemini AI","Multi-model NLP→SQL with automatic fallback. Powers all AI features."),
        ("🗄️","SQLite3","Serverless DB engine. Supports built-in and user-uploaded databases."),
        ("🌐","Streamlit","Python web framework for fast, interactive UI with session state."),
        ("📊","Plotly","6 chart types — Bar, Line, Pie, Area, Scatter, Heatmap, Histogram."),
        ("🐍","Python","Backend: AI calls, SQL safety guard, email SMTP, language detection."),
        ("📄","Pandas","Data manipulation, DataFrame rendering and CSV/HTML export."),
    ]
    for i in range(0, len(tech), 3):
        cols = st.columns(3)
        for col,(icon,title,desc) in zip(cols, tech[i:i+3]):
            with col:
                st.markdown(f'<div class="tech-card"><span class="tech-icon">{icon}</span><div class="tech-name">{title}</div><div class="tech-desc">{desc}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">🗃️ Database Schema</div>', unsafe_allow_html=True)
    sc, sd = st.columns([1,1])
    with sc:
        st.markdown("""
<div class="schema-box">
  <div class="schema-title">STUDENT Table Structure</div>
  <table style="width:100%;font-size:0.85rem;border-collapse:collapse;">
    <thead><tr style="color:#00E676;border-bottom:1px solid rgba(0,230,118,0.2);">
      <th style="padding:6px 8px;text-align:left;">Column</th>
      <th style="padding:6px 8px;text-align:left;">Type</th>
      <th style="padding:6px 8px;text-align:left;">Description</th>
    </tr></thead>
    <tbody style="color:#E0E0F0;">
      <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:6px 8px;font-family:'JetBrains Mono',monospace;color:#00BCD4;">NAME</td>
        <td style="padding:6px 8px;color:#888;">VARCHAR(50)</td>
        <td style="padding:6px 8px;">Student full name</td>
      </tr>
      <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:6px 8px;font-family:'JetBrains Mono',monospace;color:#00BCD4;">CLASS</td>
        <td style="padding:6px 8px;color:#888;">VARCHAR(30)</td>
        <td style="padding:6px 8px;">CSE / Data Science / AIML / CSE-AIML / CAI</td>
      </tr>
      <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:6px 8px;font-family:'JetBrains Mono',monospace;color:#00BCD4;">SECTION</td>
        <td style="padding:6px 8px;color:#888;">VARCHAR(5)</td>
        <td style="padding:6px 8px;">Section A, B, or C</td>
      </tr>
      <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:6px 8px;font-family:'JetBrains Mono',monospace;color:#00BCD4;">GENDER</td>
        <td style="padding:6px 8px;color:#888;">VARCHAR(10)</td>
        <td style="padding:6px 8px;">Male or Female</td>
      </tr>
      <tr>
        <td style="padding:6px 8px;font-family:'JetBrains Mono',monospace;color:#00BCD4;">MARKS</td>
        <td style="padding:6px 8px;color:#888;">INT</td>
        <td style="padding:6px 8px;">Score out of 100</td>
      </tr>
    </tbody>
  </table>
</div>
""", unsafe_allow_html=True)
    with sd:
        try:
            conn = sqlite3.connect("student.db")
            df   = pd.read_sql_query("SELECT * FROM STUDENT", conn); conn.close()
            st.markdown('<div class="section-header">Live Records</div>', unsafe_allow_html=True)
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(str(e))

# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════
def main():
    st.set_page_config(page_title="IntelliSQL", page_icon="🗄️", layout="wide", initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()

    # ── Sidebar ──
    with st.sidebar:
        # Logo — inline icon + title like reference image
        st.markdown("""
<div class="sidebar-logo">
  <div class="sidebar-logo-row">
    <span class="logo-icon">🗄️</span>
    <span class="logo-title">Intelli<span>SQL</span></span>
  </div>
  <div class="logo-sub">AI-Powered SQL Assistant</div>
</div>
""", unsafe_allow_html=True)

        pages = {
            "🏠 Home":      page_home,
            "🔍 Query":     page_query,
            "📊 Dashboard": page_dashboard,
            "💬 Chatbot":   page_chatbot,
            "➕ Manage":    page_manage,
            "📁 Upload":    page_upload,
            "ℹ️ About":     page_about,
        }

        # st.radio navigation — keeps default circles like reference image
        sel = st.radio("🧭 Navigation", list(pages.keys()), label_visibility="visible")

        # Footer matching reference image
        st.markdown("""
<div class="sidebar-footer">
  <span class="footer-powered">Powered by</span>
  <span class="footer-brand">Google Gemini AI</span>
  <span class="footer-stack">SQLite3 + Streamlit + Plotly</span>
  <span class="footer-copy">© 2025 IntelliSQL</span>
</div>
""", unsafe_allow_html=True)

    pages[sel]()

if __name__ == "__main__":
    main()