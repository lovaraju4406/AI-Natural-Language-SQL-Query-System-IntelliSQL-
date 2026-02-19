from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os, sqlite3, re, smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
from google import genai

# ── Gemini Client ────────────────────────────────────────────
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

MODELS = [
    "models/gemini-2.0-flash-lite",
    "models/gemini-2.0-flash-lite-001",
    "models/gemini-2.0-flash-001",
    "models/gemini-2.0-flash",
    "models/gemini-flash-lite-latest",
    "models/gemini-flash-latest",
]

# ── Base SQL Prompt ──────────────────────────────────────────
BASE_PROMPT = """
You are an expert SQL assistant. The SQLite database table is named STUDENT with these columns:
  NAME    (text)    — student full name
  CLASS   (text)    — department: CSE, Data Science, AIML, CSE-AIML, CAI
  SECTION (text)    — section: A, B, or C
  GENDER  (text)    — Male or Female
  MARKS   (integer) — score out of 100

Convert the user's question into a valid SQL query.

Examples:
- "How many students?"                      → SELECT COUNT(*) FROM STUDENT;
- "All CSE students"                        → SELECT * FROM STUDENT WHERE CLASS='CSE';
- "All Data Science students"               → SELECT * FROM STUDENT WHERE CLASS='Data Science';
- "All AIML students"                       → SELECT * FROM STUDENT WHERE CLASS='AIML';
- "All CSE-AIML students"                   → SELECT * FROM STUDENT WHERE CLASS='CSE-AIML';
- "All CAI students"                        → SELECT * FROM STUDENT WHERE CLASS='CAI';
- "Section A students"                      → SELECT * FROM STUDENT WHERE SECTION='A';
- "All female students"                     → SELECT * FROM STUDENT WHERE GENDER='Female';
- "All male students"                       → SELECT * FROM STUDENT WHERE GENDER='Male';
- "Average marks"                           → SELECT ROUND(AVG(MARKS),1) AS AVG_MARKS FROM STUDENT;
- "Highest marks"                           → SELECT * FROM STUDENT WHERE MARKS=(SELECT MAX(MARKS) FROM STUDENT);
- "Students with marks above 80"            → SELECT * FROM STUDENT WHERE MARKS > 80;
- "Class wise average"                      → SELECT CLASS, ROUND(AVG(MARKS),1) AS AVG_MARKS FROM STUDENT GROUP BY CLASS ORDER BY AVG_MARKS DESC;
- "Section wise count"                      → SELECT CLASS, SECTION, COUNT(*) AS COUNT FROM STUDENT GROUP BY CLASS, SECTION ORDER BY CLASS, SECTION;
- "Gender wise count"                       → SELECT GENDER, COUNT(*) AS COUNT FROM STUDENT GROUP BY GENDER;
- "Top 5 students"                          → SELECT * FROM STUDENT ORDER BY MARKS DESC LIMIT 5;
- "Girls in CSE section A"                  → SELECT * FROM STUDENT WHERE CLASS='CSE' AND SECTION='A' AND GENDER='Female';
- "Pass count per department"               → SELECT CLASS, COUNT(*) AS PASS FROM STUDENT WHERE MARKS>=40 GROUP BY CLASS;
- "Students between 60 and 80 marks"        → SELECT * FROM STUDENT WHERE MARKS BETWEEN 60 AND 80;
- "Count of students per department"        → SELECT CLASS, COUNT(*) AS TOTAL FROM STUDENT GROUP BY CLASS ORDER BY TOTAL DESC;

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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

:root {
    --green:   #00E676;
    --green2:  #00C853;
    --green3:  #00897B;
    --dark1:   #0D0D1A;
    --dark2:   #12122A;
    --dark3:   #1A1A40;
    --dark4:   #222260;
    --purple:  #6C3FC5;
    --purple2: #4527A0;
    --text:    #E0E0E0;
    --muted:   #8888AA;
    --border:  rgba(0,230,118,0.25);
    --glow:    rgba(0,230,118,0.15);
}

*, html, body { box-sizing: border-box; }

.stApp {
    background: var(--dark1) !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--dark2) 0%, var(--dark3) 100%) !important;
    border-right: 1px solid var(--border) !important;
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] * { color: var(--text) !important; }
section[data-testid="stSidebar"] .stRadio > div { gap: 2px; }
section[data-testid="stSidebar"] .stRadio label {
    padding: 8px 12px !important;
    border-radius: 8px !important;
    transition: background 0.2s !important;
    cursor: pointer !important;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: var(--glow) !important;
}

/* ── Hide chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, var(--green2) 0%, var(--green3) 100%) !important;
    color: #000 !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 20px !important;
    font-size: 0.92em !important;
    width: 100%;
    letter-spacing: 0.3px;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 12px var(--glow);
}
.stButton > button:hover {
    transform: translateY(-2px) scale(1.01) !important;
    box-shadow: 0 6px 24px rgba(0,200,83,0.4) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Download button ── */
.stDownloadButton > button {
    background: transparent !important;
    color: var(--green) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    width: 100%;
    transition: all 0.2s ease !important;
}
.stDownloadButton > button:hover {
    background: var(--glow) !important;
    border-color: var(--green2) !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input {
    background: var(--dark3) !important;
    color: var(--text) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95em !important;
    transition: all 0.2s ease !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--green2) !important;
    box-shadow: 0 0 0 3px var(--glow) !important;
    outline: none !important;
}
.stTextInput label, .stTextArea label,
.stSelectbox label, .stNumberInput label {
    color: var(--muted) !important;
    font-weight: 500 !important;
    font-size: 0.85em !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: var(--dark3) !important;
    color: var(--text) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 10px !important;
}

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, var(--dark3) 0%, var(--purple2) 50%, var(--dark3) 100%);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 44px 36px;
    text-align: center;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at center, rgba(0,230,118,0.05) 0%, transparent 60%);
    pointer-events: none;
}
.hero-icon  { font-size: 3.2em; margin-bottom: 8px; }
.hero-title { color: var(--green); font-size: 2.6em; font-weight: 900; letter-spacing: -1px; line-height: 1.1; }
.hero-sub   { color: var(--muted); font-size: 1.05em; margin-top: 8px; font-weight: 400; }

/* ── Section header ── */
.sec-head {
    color: var(--green);
    font-size: 1.1em;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    margin: 28px 0 14px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.sec-head::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
    margin-left: 8px;
}

/* ── Cards ── */
.card {
    background: var(--dark3);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 14px;
    transition: all 0.25s ease;
    position: relative;
    overflow: hidden;
}
.card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, var(--green2), var(--purple));
    border-radius: 14px 0 0 14px;
}
.card:hover {
    border-color: rgba(0,230,118,0.5);
    box-shadow: 0 8px 32px var(--glow);
    transform: translateY(-2px);
}
.card-icon  { font-size: 1.8em; margin-bottom: 8px; }
.card-title { color: var(--text); font-size: 1em; font-weight: 700; margin-bottom: 5px; }
.card-desc  { color: var(--muted); font-size: 0.85em; line-height: 1.55; }

/* ── Metric box ── */
.metric {
    background: var(--dark3);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px 16px;
    text-align: center;
    transition: all 0.2s ease;
}
.metric:hover { box-shadow: 0 4px 20px var(--glow); transform: translateY(-2px); }
.metric-val { color: var(--green); font-size: 2.2em; font-weight: 900; line-height: 1; }
.metric-lbl { color: var(--muted); font-size: 0.78em; font-weight: 500; margin-top: 6px; text-transform: uppercase; letter-spacing: 0.5px; }

/* ── Badge ── */
.badge {
    display: inline-block;
    background: rgba(0,200,83,0.1);
    border: 1px solid var(--border);
    color: var(--green);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.78em;
    font-weight: 600;
    margin: 3px;
}

/* ── Tip box ── */
.tip {
    background: var(--dark3);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 18px;
    color: var(--text);
    font-size: 0.88em;
    line-height: 2;
}
.tip .t-head { color: var(--green); font-weight: 700; font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }

/* ── Chat bubbles ── */
.cb-user {
    background: linear-gradient(135deg, var(--dark4), var(--purple2));
    border: 1px solid var(--border);
    border-radius: 18px 18px 4px 18px;
    padding: 12px 16px;
    margin: 10px 0 10px 80px;
    color: var(--text);
    font-size: 0.93em;
    box-shadow: 0 2px 12px var(--glow);
}
.cb-ai {
    background: var(--dark3);
    border: 1px solid var(--border);
    border-radius: 18px 18px 18px 4px;
    padding: 12px 16px;
    margin: 10px 80px 10px 0;
    color: var(--text);
    font-size: 0.93em;
}
.cb-label { font-size: 0.73em; color: var(--muted); margin-bottom: 5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }

/* ── History item ── */
.hist {
    background: var(--dark3);
    border-left: 3px solid var(--green2);
    border-radius: 0 10px 10px 0;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 0.85em;
}
.hist-q   { color: var(--green); font-weight: 600; margin-bottom: 3px; }
.hist-sql { color: var(--muted); font-family: 'Courier New', monospace; font-size: 0.82em; }

/* ── Step ── */
.step {
    background: var(--dark3);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
    height: 100%;
}
.step-num { color: var(--green); font-size: 1.6em; font-weight: 900; }
.step-txt { color: var(--muted); font-size: 0.85em; margin-top: 6px; line-height: 1.5; }

/* ── Chip buttons — chip row ── */
.chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
.chip {
    background: var(--dark3);
    border: 1px solid var(--border);
    color: var(--green) !important;
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 0.82em;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.18s ease;
    white-space: nowrap;
}
.chip:hover { background: var(--glow); border-color: var(--green2); }

/* ── Code block ── */
.stCode { border: 1px solid var(--border) !important; border-radius: 10px !important; }
pre { border-radius: 10px !important; }

/* ── Alert ── */
.stAlert { border-radius: 10px !important; }

/* ── Dataframe ── */
.stDataFrame { border: 1px solid var(--border) !important; border-radius: 10px; }

/* ── Sidebar logo ── */
.sb-logo {
    background: linear-gradient(135deg, var(--dark3), var(--dark4));
    border-bottom: 1px solid var(--border);
    padding: 20px 16px;
    margin-bottom: 16px;
}
.sb-logo-title { color: var(--green); font-size: 1.4em; font-weight: 900; letter-spacing: 1px; }
.sb-logo-sub   { color: var(--muted); font-size: 0.72em; margin-top: 2px; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: var(--green2) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--dark2); }
::-webkit-scrollbar-thumb { background: var(--dark4); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: var(--green3); }

/* ── Expander ── */
.streamlit-expanderHeader {
    background: var(--dark3) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-weight: 600 !important;
}
.streamlit-expanderContent {
    background: var(--dark2) !important;
    border: 1px solid var(--border) !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
}

/* ── Radio in sidebar active ── */
.stRadio [data-baseweb="radio"] { gap: 6px !important; }
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
    ex = f"<h3>💡 Explanation</h3><p>{explanation}</p>" if explanation else ""
    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><title>IntelliSQL Report</title>
<style>body{{font-family:Inter,Arial,sans-serif;background:#0D0D1A;color:#E0E0E0;padding:40px;max-width:1200px;margin:0 auto}}
h1,h2,h3{{color:#00E676}}pre{{background:#1A1A40;padding:16px;border-radius:10px;color:#00E676;font-size:.9em}}
table{{border-collapse:collapse;width:100%;margin-top:12px;border-radius:10px;overflow:hidden}}
th{{background:#1A1A40;color:#00E676;padding:10px 14px;text-align:left;border:1px solid rgba(0,230,118,.2)}}
td{{padding:10px 14px;border:1px solid rgba(255,255,255,.06);color:#E0E0E0}}
tr:nth-child(even){{background:rgba(255,255,255,.03)}}.badge{{background:rgba(0,200,83,.1);border:1px solid rgba(0,230,118,.3);color:#00E676;border-radius:20px;padding:3px 10px;font-size:.8em}}</style>
</head><body>
<h1>🗄️ IntelliSQL Query Report</h1>
<p><span class="badge">{datetime.now().strftime('%Y-%m-%d %H:%M')}</span></p><hr>
<h2>❓ Question</h2><p>{question}</p>
<h2>🧾 Generated SQL</h2><pre>{sql}</pre>{ex}
<h2>📊 Results <span class="badge">{len(df)} rows</span></h2>
<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>
<br><p style='color:#444;font-size:.8em'>Generated by IntelliSQL — Powered by Google Gemini AI</p>
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
    st.markdown('<div class="sec-head">📈 Visualization</div>', unsafe_allow_html=True)
    o1, o2, o3 = st.columns(3)
    with o1: ctype = st.selectbox("Type", ["Bar","Line","Pie","Area","Scatter"], key=f"{prefix}ct")
    with o2: y = st.selectbox("Value (Y)", numeric, key=f"{prefix}y")
    with o3: x = st.selectbox("Label (X)", df.columns.tolist(), key=f"{prefix}x")
    try:
        import plotly.express as px
        kw = dict(template="plotly_dark", color_discrete_sequence=["#00E676","#00C853","#6C3FC5","#0F3460","#E91E63"])
        gl = dict(plot_bgcolor="#12122A", paper_bgcolor="#12122A", font_color="#E0E0E0",
                  title_font_color="#00E676", title_font_size=15,
                  margin=dict(l=20,r=20,t=40,b=20))
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
        else: st.line_chart(df.set_index(x)[y])
        st.caption("Install plotly for richer charts: `pip install plotly`")

def init_state():
    defaults = {"history":[], "chat":[], "chip_q":"", "last_sql":"", "last_df":None}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def metric_card(val, label):
    return f'<div class="metric"><div class="metric-val">{val}</div><div class="metric-lbl">{label}</div></div>'

# ════════════════════════════════════════════════════════════
# PAGE: HOME
# ════════════════════════════════════════════════════════════
def page_home():
    st.markdown(CSS, unsafe_allow_html=True)

    # Hero
    st.markdown("""
    <div class="hero">
        <div class="hero-icon">🗄️</div>
        <div class="hero-title">IntelliSQL</div>
        <div class="hero-sub">Ask questions in plain English — get instant SQL results, charts & AI insights</div>
        <br>
        <span class="badge">🤖 Gemini AI</span>
        <span class="badge">🐍 Python</span>
        <span class="badge">🗄️ SQLite</span>
        <span class="badge">🌐 Streamlit</span>
        <span class="badge">📊 Plotly</span>
        <span class="badge">🌍 Multi-lang</span>
        <span class="badge">🛡️ SQL Guard</span>
    </div>
    """, unsafe_allow_html=True)

    # Live stats
    total, avg_m, top_m, cls, pass_r = db_stats()
    st.markdown('<div class="sec-head">📊 Live Stats</div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5)
    for col, v, l in zip([c1,c2,c3,c4,c5],
        [total, avg_m, top_m, cls, f"{pass_r}%"],
        ["Students","Avg Marks","Top Score","Classes","Pass Rate"]):
        with col: st.markdown(metric_card(v,l), unsafe_allow_html=True)

    # Features
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-head">✨ Features</div>', unsafe_allow_html=True)
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
            st.markdown(f'<div class="card"><div class="card-icon">{icon}</div><div class="card-title">{title}</div><div class="card-desc">{desc}</div></div>', unsafe_allow_html=True)

    # How it works
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-head">⚙️ How It Works</div>', unsafe_allow_html=True)
    steps = [("1","Type your question\nin any language"),("2","Gemini AI converts\nit to safe SQL"),
             ("3","SQL runs on your\nSQLite database"),("4","See results, charts\n& AI insights")]
    for col,(n,d) in zip(st.columns(4),steps):
        with col:
            st.markdown(f'<div class="step"><div class="step-num">{n}</div><div class="step-txt">{d}</div></div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: QUERY
# ════════════════════════════════════════════════════════════
def page_query():
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()

    st.markdown("""<div class="hero" style="padding:28px 36px">
        <div class="hero-icon">🔍</div>
        <div class="hero-title" style="font-size:2em">Query Assistant</div>
        <div class="hero-sub">Ask in any language — get SQL, insights, charts & exports</div>
    </div>""", unsafe_allow_html=True)

    # Chips
    chips = [
        "How many students?","All CSE students","Highest marks?",
        "Average marks?","All AIML students","Section A students",
        "All female students","All male students","CSE-AIML students",
        "Top 5 students","CAI students","Class-wise average marks",
        "Marks above 80?","Marks below 50?","Gender-wise count",
        "Section wise count","Data Science students","Pass count by class",
    ]
    st.markdown('<div class="sec-head">🧩 Quick Queries</div>', unsafe_allow_html=True)
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
        go = st.button("⚡  Generate & Run", key="go_btn")

        if go:
            st.session_state.chip_q = ""
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                # Language detection & translation
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

                # Generate SQL
                with st.spinner("🤖 Generating SQL..."):
                    try:
                        sql = nl_to_sql(q_eng)
                        # Strip any accidental backticks
                        sql = re.sub(r"```sql|```","", sql).strip()
                        if not sql.endswith(";"): sql += ";"
                    except Exception as e:
                        st.error(f"❌ AI Error: {e}")
                        sql = None

                if sql:
                    # Safety check
                    if not is_safe_sql(sql):
                        st.error("🛡️ **Blocked!** Dangerous SQL operation detected (DROP/DELETE/INSERT/UPDATE). Query rejected for safety.")
                    else:
                        st.session_state.last_sql = sql
                        st.markdown('<div class="sec-head">🧾 Generated SQL</div>', unsafe_allow_html=True)
                        st.code(sql, language="sql")

                        # Tabs for AI tools
                        tab1, tab2, tab3 = st.tabs(["💡 Explain", "⚡ Optimize", "🧠 Insights"])

                        with tab1:
                            with st.spinner("Explaining..."):
                                expl = explain_sql(sql)
                            st.markdown(f'<div class="tip"><div class="t-head">What this query does</div>{expl}</div>', unsafe_allow_html=True)

                        # Execute SQL
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

                                # Metrics
                                st.markdown('<div class="sec-head">📊 Results</div>', unsafe_allow_html=True)
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
                                    st.markdown(f'<div class="tip"><div class="t-head">AI Data Insights</div>{ins}</div>', unsafe_allow_html=True)

                                with tab2:
                                    with st.spinner("Optimizing..."):
                                        opt = optimize_sql(sql)
                                    st.markdown(f'<div class="tip"><div class="t-head">Optimization Suggestion</div>{opt}</div>', unsafe_allow_html=True)

                                # Export row
                                st.markdown('<div class="sec-head">⬇️ Export</div>', unsafe_allow_html=True)
                                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                                ex1, ex2 = st.columns(2)
                                with ex1:
                                    st.download_button("📥 Download CSV", df.to_csv(index=False).encode(), f"results_{ts}.csv","text/csv")
                                with ex2:
                                    st.download_button("📄 HTML Report", make_html_report(question,sql,df,expl), f"report_{ts}.html","text/html")

                                # Email
                                with st.expander("📧 Email Results"):
                                    em1,em2,em3 = st.columns(3)
                                    with em1: to_a = st.text_input("Recipient Email", key="eto")
                                    with em2: su   = st.text_input("Your Gmail", key="esu")
                                    with em3: sp   = st.text_input("App Password", type="password", key="esp")
                                    if st.button("📨 Send", key="send_em"):
                                        body = f"<h2>IntelliSQL Results</h2><p><b>Question:</b> {question}</p><pre>{sql}</pre>{df.to_html(index=False)}"
                                        try:
                                            send_email(to_a, f"IntelliSQL: {question[:50]}", body, su, sp)
                                            st.success("✅ Email sent!")
                                        except Exception as ex:
                                            st.error(f"❌ {ex}")

                                # Chart
                                render_chart(df, "q_")

                                # Save history
                                st.session_state.history.insert(0,{
                                    "time": datetime.now().strftime("%H:%M:%S"),
                                    "question": question, "sql": sql, "rows": len(df)
                                })
                                st.success(f"✅ {len(df)} record(s) found.")
                            else:
                                st.info("ℹ️ No records matched your query.")

    with side_col:
        st.markdown('<div class="sec-head">🗃️ Schema</div>', unsafe_allow_html=True)
        st.markdown("""<div class="tip">
            <div class="t-head">STUDENT Table</div>
            🟢 <b>NAME</b> — Student name<br>
            🟢 <b>CLASS</b> — CSE / Data Science / AIML / CSE-AIML / CAI<br>
            🟢 <b>SECTION</b> — A, B or C<br>
            🟢 <b>GENDER</b> — Male or Female<br>
            🟢 <b>MARKS</b> — Score out of 100
        </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-head">💡 Try Asking</div>', unsafe_allow_html=True)
        st.markdown("""<div class="tip">
            📌 Top 5 students by marks<br>
            📌 Class-wise average marks<br>
            📌 All female CSE students<br>
            📌 CSE section A students<br>
            📌 Students between 60-80<br>
            📌 Gender-wise count<br>
            📌 Pass count per department<br>
            📌 Section wise student count<br>
            🇮🇳 सबसे ज्यादा marks किसके?<br>
            🇮🇳 CSE విద్యార్థులు చూపించు
        </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-head">🕓 History</div>', unsafe_allow_html=True)
        if st.session_state.history:
            if st.button("🗑️ Clear History"):
                st.session_state.history = []; st.rerun()
            for h in st.session_state.history[:5]:
                st.markdown(f'<div class="hist"><div class="hist-q">⏱ {h["time"]} — {h["question"]}</div><div class="hist-sql">{h["sql"]}</div><div style="color:#444;font-size:.75em;margin-top:3px">{h["rows"]} rows</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="tip" style="text-align:center;color:#555">No queries yet</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ════════════════════════════════════════════════════════════
def page_dashboard():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("""<div class="hero" style="padding:28px 36px">
        <div class="hero-icon">📊</div>
        <div class="hero-title" style="font-size:2em">Dashboard</div>
        <div class="hero-sub">Real-time analytics and visual insights from your student database</div>
    </div>""", unsafe_allow_html=True)

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
            st.markdown('<div class="sec-head">📚 Class Average Marks</div>', unsafe_allow_html=True)
            ca = df.groupby("CLASS")["MARKS"].mean().reset_index().rename(columns={"MARKS":"AVG"})
            ca["AVG"] = ca["AVG"].round(1)
            fig = px.bar(ca, x="CLASS", y="AVG", color="CLASS", **kw, text="AVG", title="Average Marks by Class")
            fig.update_traces(textposition="outside"); fig.update_layout(**bg)
            st.plotly_chart(fig, use_container_width=True)

        with r2:
            st.markdown('<div class="sec-head">👥 Gender Distribution</div>', unsafe_allow_html=True)
            sc = df["GENDER"].value_counts().reset_index(); sc.columns=["Gender","Count"]
            fig2 = px.pie(sc, names="Gender", values="Count", **kw,
                          title="Male vs Female Students", hole=0.45,
                          color_discrete_map={"Male":"#00E676","Female":"#6C3FC5"})
            fig2.update_layout(**bg); fig2.update_traces(textinfo="label+percent")
            st.plotly_chart(fig2, use_container_width=True)

        r2a, r2b = st.columns(2)
        with r2a:
            st.markdown('<div class="sec-head">📈 Marks Distribution</div>', unsafe_allow_html=True)
            fig3 = px.histogram(df, x="MARKS", nbins=10, color_discrete_sequence=["#00E676"],
                                template="plotly_dark", title="Frequency of Marks", labels={"MARKS":"Marks"})
            fig3.update_layout(**bg); st.plotly_chart(fig3, use_container_width=True)

        with r2b:
            st.markdown('<div class="sec-head">🏆 Top 8 Students</div>', unsafe_allow_html=True)
            t8 = df.nlargest(8,"MARKS")
            fig4 = px.bar(t8, x="NAME", y="MARKS", color="CLASS", **kw, title="Top 8 Students")
            fig4.update_layout(**bg); st.plotly_chart(fig4, use_container_width=True)

        r3a, r3b = st.columns(2)
        with r3a:
            st.markdown('<div class="sec-head">✅ Pass vs Fail by Class</div>', unsafe_allow_html=True)
            df2 = df.copy(); df2["Status"] = df2["MARKS"].apply(lambda x:"Pass ✅" if x>=40 else "Fail ❌")
            pf = df2.groupby(["CLASS","Status"])["NAME"].count().reset_index()
            pf.columns=["CLASS","Status","Count"]
            fig5 = px.bar(pf, x="CLASS", y="Count", color="Status", barmode="group",
                          template="plotly_dark", color_discrete_map={"Pass ✅":"#00E676","Fail ❌":"#E91E63"},
                          title="Pass vs Fail per Class")
            fig5.update_layout(**bg); st.plotly_chart(fig5, use_container_width=True)

        with r3b:
            st.markdown('<div class="sec-head">🔥 Marks Heatmap</div>', unsafe_allow_html=True)
            hm = df.groupby(["CLASS","SECTION"])["MARKS"].mean().reset_index()
            hp = hm.pivot(index="CLASS",columns="SECTION",values="MARKS").fillna(0).round(1)
            fig6 = px.imshow(hp, color_continuous_scale="Greens", template="plotly_dark",
                             title="Avg Marks — Class × Section", text_auto=True)
            fig6.update_layout(**bg); st.plotly_chart(fig6, use_container_width=True)

    except ImportError:
        st.warning("Install plotly for charts: `pip install plotly`")

    st.markdown('<div class="sec-head">📋 Full Records</div>', unsafe_allow_html=True)
    st.dataframe(df.sort_values("MARKS",ascending=False), use_container_width=True, hide_index=True)
    st.download_button("📥 Download All CSV", df.to_csv(index=False).encode(), "students.csv","text/csv")

# ════════════════════════════════════════════════════════════
# PAGE: CHATBOT
# ════════════════════════════════════════════════════════════
def page_chatbot():
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()

    st.markdown("""<div class="hero" style="padding:28px 36px">
        <div class="hero-icon">💬</div>
        <div class="hero-title" style="font-size:2em">AI Chatbot</div>
        <div class="hero-sub">Multi-turn SQL conversation — ask follow-up questions with full memory</div>
    </div>""", unsafe_allow_html=True)

    if st.button("🗑️ New Chat"):
        st.session_state.chat = []; st.rerun()

    # Render chat
    for msg in st.session_state.chat:
        if msg["role"] == "user":
            st.markdown(f'<div class="cb-user"><div class="cb-label">👤 You</div>{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="cb-ai"><div class="cb-label">🤖 IntelliSQL</div>{msg["content"]}</div>', unsafe_allow_html=True)
            if msg.get("df") is not None:
                st.dataframe(msg["df"], use_container_width=True, hide_index=True)

    user_input = st.chat_input("Ask about the student database... (e.g. 'Now filter only section A')")
    if user_input:
        st.session_state.chat.append({"role":"user","content":user_input})

        # Build context-aware prompt
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
    st.markdown("""<div class="hero" style="padding:28px 36px">
        <div class="hero-icon">➕</div>
        <div class="hero-title" style="font-size:2em">Manage Data</div>
        <div class="hero-sub">Add new students or remove existing records from the database</div>
    </div>""", unsafe_allow_html=True)

    add_col, del_col = st.columns(2)

    with add_col:
        st.markdown('<div class="sec-head">➕ Add Student</div>', unsafe_allow_html=True)
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
                    except Exception as e: st.error(f"❌ {e}")

    with del_col:
        st.markdown('<div class="sec-head">🗑️ Delete Student</div>', unsafe_allow_html=True)
        try:
            conn = sqlite3.connect("student.db")
            df_all = pd.read_sql_query("SELECT rowid,* FROM STUDENT ORDER BY NAME", conn); conn.close()
            if df_all.empty:
                st.info("No students in database.")
            else:
                opts = {f"{r['NAME']}  |  {r['CLASS']}  |  Sec {r['SECTION']}  |  {r['MARKS']} marks": r["rowid"]
                        for _,r in df_all.iterrows()}
                sel = st.selectbox("Select student:", list(opts.keys()))
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Delete Selected Student"):
                    conn = sqlite3.connect("student.db")
                    conn.cursor().execute("DELETE FROM STUDENT WHERE rowid=?",(opts[sel],))
                    conn.commit(); conn.close()
                    st.success("✅ Deleted successfully!")
                    st.cache_data.clear(); st.rerun()
        except Exception as e: st.error(f"❌ {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="sec-head">📋 All Records</div>', unsafe_allow_html=True)
    try:
        df_s = load_all_students()
        c1,c2,c3,c4 = st.columns(4)
        for col,v,l in zip([c1,c2,c3,c4],
            [len(df_s), round(df_s["MARKS"].mean(),1) if not df_s.empty else 0,
             df_s["MARKS"].max() if not df_s.empty else 0, df_s["CLASS"].nunique() if not df_s.empty else 0],
            ["Total","Avg Marks","Highest","Classes"]):
            with col: st.markdown(metric_card(v,l), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.dataframe(df_s.sort_values("MARKS",ascending=False), use_container_width=True, hide_index=True)
        st.download_button("📥 Export CSV", df_s.to_csv(index=False).encode(),"students.csv","text/csv")
    except Exception as e: st.error(f"❌ {e}")

# ════════════════════════════════════════════════════════════
# PAGE: UPLOAD
# ════════════════════════════════════════════════════════════
def page_upload():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("""<div class="hero" style="padding:28px 36px">
        <div class="hero-icon">📁</div>
        <div class="hero-title" style="font-size:2em">Upload & Query</div>
        <div class="hero-sub">Upload any SQLite .db or CSV file and query it with natural language</div>
    </div>""", unsafe_allow_html=True)

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
                st.markdown(f'<div class="tip">{qs}</div>', unsafe_allow_html=True)

            tmp = "/tmp/csv_upload.db"
            ct = sqlite3.connect(tmp); df_c.to_sql("my_table",ct,if_exists="replace",index=False); ct.close()
            cp = f"Table: my_table. Columns: {', '.join(df_c.columns)}. Return ONLY raw SQL. No ``` or sql word."

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
                        else: st.info("No results.")
                    except Exception as e: st.error(f"❌ {e}")

    else:
        up_db = st.file_uploader("Upload .db file", type=["db"])
        if up_db:
            tmp_db = f"/tmp/{up_db.name}"
            with open(tmp_db,"wb") as f: f.write(up_db.read())
            try:
                conn = sqlite3.connect(tmp_db)
                tables = [t[0] for t in conn.cursor().execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                conn.close()
                st.success(f"✅ {len(tables)} table(s) found: {', '.join(tables)}")
                tbl = st.selectbox("Choose table:", tables)
                conn = sqlite3.connect(tmp_db)
                df_p = pd.read_sql_query(f"SELECT * FROM '{tbl}' LIMIT 8", conn); conn.close()
                st.dataframe(df_p, use_container_width=True, hide_index=True)

                with st.expander("📝 AI-Generated Sample Questions"):
                    with st.spinner("Generating..."):
                        qs2 = auto_sample_questions(f"table '{tbl}' with columns: {', '.join(df_p.columns.tolist())}")
                    st.markdown(f'<div class="tip">{qs2}</div>', unsafe_allow_html=True)

                dp = f"Table: {tbl}. Columns: {', '.join(df_p.columns)}. Return ONLY raw SQL. No ``` or sql word."
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
                            else: st.info("No results.")
                        except Exception as e: st.error(f"❌ {e}")
            except Exception as e: st.error(f"❌ {e}")

# ════════════════════════════════════════════════════════════
# PAGE: ABOUT
# ════════════════════════════════════════════════════════════
def page_about():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("""<div class="hero" style="padding:28px 36px">
        <div class="hero-icon">ℹ️</div>
        <div class="hero-title" style="font-size:2em">About</div>
        <div class="hero-sub">Technology stack, architecture and database schema</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec-head">🎯 What is IntelliSQL?</div>', unsafe_allow_html=True)
    st.markdown("""<div class="card" style="padding:24px">
        <div class="card-desc" style="font-size:.95em;line-height:1.8">
        <b style="color:#00E676">IntelliSQL</b> is a production-grade AI-powered Natural Language to SQL platform.
        It uses <b style="color:#00E676">Google Gemini</b> to convert plain English questions (in any language) into
        precise SQL queries, executes them on SQLite, and returns results with charts, AI insights, and export options.
        <br><br>Built for students, teachers, and data analysts who want to explore databases
        without writing a single line of SQL.
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec-head">🛠️ Tech Stack</div>', unsafe_allow_html=True)
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
                st.markdown(f'<div class="card" style="text-align:center"><div style="font-size:2em;margin-bottom:8px">{icon}</div><div class="card-title">{title}</div><div class="card-desc">{desc}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="sec-head">🗃️ Database Schema</div>', unsafe_allow_html=True)
    sc, sd = st.columns([1,1])
    with sc:
        st.markdown("""<div class="card"><div class="card-title" style="margin-bottom:14px">STUDENT Table Structure</div>
        <table style="width:100%;border-collapse:collapse;color:#E0E0E0;font-size:.9em">
        <tr style="border-bottom:1px solid rgba(0,230,118,.3)">
            <th style="color:#00E676;padding:8px;text-align:left">Column</th>
            <th style="color:#00E676;padding:8px;text-align:left">Type</th>
            <th style="color:#00E676;padding:8px;text-align:left">Description</th>
        </tr>
        <tr style="border-bottom:1px solid rgba(255,255,255,.06)"><td style="padding:8px">NAME</td><td style="padding:8px;color:#8888AA">VARCHAR(50)</td><td style="padding:8px">Student full name</td></tr>
        <tr style="border-bottom:1px solid rgba(255,255,255,.06)"><td style="padding:8px">CLASS</td><td style="padding:8px;color:#8888AA">VARCHAR(30)</td><td style="padding:8px">CSE / Data Science / AIML / CSE-AIML / CAI</td></tr>
        <tr style="border-bottom:1px solid rgba(255,255,255,.06)"><td style="padding:8px">SECTION</td><td style="padding:8px;color:#8888AA">VARCHAR(5)</td><td style="padding:8px">Section A, B, or C</td></tr>
        <tr style="border-bottom:1px solid rgba(255,255,255,.06)"><td style="padding:8px">GENDER</td><td style="padding:8px;color:#8888AA">VARCHAR(10)</td><td style="padding:8px">Male or Female</td></tr>
        <tr><td style="padding:8px">MARKS</td><td style="padding:8px;color:#8888AA">INT</td><td style="padding:8px">Score out of 100</td></tr>
        </table></div>""", unsafe_allow_html=True)
    with sd:
        try:
            conn = sqlite3.connect("student.db")
            df = pd.read_sql_query("SELECT * FROM STUDENT", conn); conn.close()
            st.markdown('<div style="color:#00E676;font-weight:700;font-size:.9em;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">Live Records</div>', unsafe_allow_html=True)
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e: st.error(str(e))

# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════
def main():
    st.set_page_config(page_title="IntelliSQL", page_icon="🗄️", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()

    # Sidebar
    st.sidebar.markdown("""
    <div class="sb-logo">
        <div class="sb-logo-title">🗄️ IntelliSQL</div>
        <div class="sb-logo-sub">AI-Powered SQL Assistant</div>
    </div>
    """, unsafe_allow_html=True)

    pages = {
        "🏠  Home":       page_home,
        "🔍  Query":      page_query,
        "📊  Dashboard":  page_dashboard,
        "💬  Chatbot":    page_chatbot,
        "➕  Manage":     page_manage,
        "📁  Upload":     page_upload,
        "ℹ️  About":      page_about,
    }

    sel = st.sidebar.radio("", list(pages.keys()), label_visibility="collapsed")

    # Sidebar footer
    total, avg_m, top_m, cls, pass_r = db_stats()
    st.sidebar.markdown(f"""
    <div style="margin-top:20px;padding:14px;background:rgba(0,230,118,.05);border:1px solid rgba(0,230,118,.15);border-radius:10px;font-size:.78em;">
        <div style="color:#00E676;font-weight:700;margin-bottom:8px">📊 Quick Stats</div>
        <div style="color:#8888AA">👥 {total} Students</div>
        <div style="color:#8888AA">📈 Avg: {avg_m} marks</div>
        <div style="color:#8888AA">🏆 Top: {top_m} marks</div>
        <div style="color:#8888AA">✅ Pass rate: {pass_r}%</div>
    </div>
    <div style="margin-top:14px;color:#444;font-size:.72em;text-align:center">
        🤖 Gemini AI · 🗄️ SQLite<br>🌐 Streamlit · 📊 Plotly<br><br>© 2025 IntelliSQL
    </div>
    """, unsafe_allow_html=True)

    pages[sel]()

if __name__ == "__main__":
    main()