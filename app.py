import json
import os
import random
import sqlite3
from datetime import datetime
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

try:
    from groq import Groq
except ImportError:
    Groq = None


# ---------------------------------------------------------
# APP CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="CyberQuest AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_TITLE = "CyberQuest AI"
DB_PATH = "cyberquest.db"

st.markdown(
    """
    <style>
    .main { background-color: #0b1220; }
    [data-testid="stSidebar"] { background-color: #101a2c; }
    .hero {
        padding: 1.6rem;
        border-radius: 18px;
        background: linear-gradient(120deg, #142b4d, #173d48);
        border: 1px solid #28556b;
        margin-bottom: 1rem;
    }
    .hero h1 { margin-bottom: .2rem; }
    .small-muted { color: #aab8ca; }
    div.stButton > button { border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_database():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                scenario_id TEXT NOT NULL,
                scenario_title TEXT NOT NULL,
                category TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                selected_option TEXT NOT NULL,
                correct INTEGER NOT NULL,
                points INTEGER NOT NULL,
                completed_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def ensure_user(username):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users(username, created_at) VALUES (?, ?)",
            (username, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()


def save_attempt(username, scenario, selected_option, correct, points):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO attempts (
                username, scenario_id, scenario_title, category, difficulty,
                selected_option, correct, points, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                scenario["id"],
                scenario["title"],
                scenario["category"],
                scenario["difficulty"],
                selected_option,
                int(correct),
                points,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()


def get_user_stats(username):
    with get_connection() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM attempts WHERE username = ? ORDER BY completed_at DESC",
            conn,
            params=(username,),
        )
    if df.empty:
        return df, {"attempts": 0, "correct": 0, "points": 0, "accuracy": 0}
    stats = {
        "attempts": int(len(df)),
        "correct": int(df["correct"].sum()),
        "points": int(df["points"].sum()),
        "accuracy": round(float(df["correct"].mean()) * 100, 1),
    }
    return df, stats


# ---------------------------------------------------------
# SCENARIO LIBRARY
# ---------------------------------------------------------
SCENARIOS = [
    {
        "id": "email-01",
        "title": "The University Account Warning",
        "category": "Phishing",
        "difficulty": "Beginner",
        "story": (
            "You receive an email saying your university account will be "
            "blocked in 30 minutes unless you verify your identity using a link. "
            "You were not expecting this message."
        ),
        "question": "What is the safest first action?",
        "options": [
            "Click the link quickly before the deadline.",
            "Check the sender and contact the university through its official website or help desk.",
            "Reply with your password to prove that the account belongs to you.",
            "Forward the email to friends and ask them to click it.",
        ],
        "answer": 1,
        "explanation": (
            "Correct. Urgent threats and unexpected verification links are common "
            "warning signs. Do not use the link in the message. Check the sender "
            "and contact the university through a trusted, official channel."
        ),
        "why_wrong": {
            0: "A deadline that pressures you to act immediately can be a warning sign. Verify the request independently.",
            2: "A legitimate support team should never ask you to send your password by email.",
            3: "Forwarding a suspicious link can expose other people to the same risk.",
        },
    },
    {
        "id": "password-01",
        "title": "The Reused Password",
        "category": "Password Security",
        "difficulty": "Beginner",
        "story": (
            "You use the same password for your email, gaming account, and "
            "university portal. A service you use announces that some account "
            "information may have been exposed."
        ),
        "question": "What should you do?",
        "options": [
            "Keep using the password because it is easy to remember.",
            "Change the password only on the least important account.",
            "Use unique passwords for each account and enable multifactor authentication.",
            "Share the password with a friend so they can check your accounts.",
        ],
        "answer": 2,
        "explanation": (
            "Correct. Unique passwords reduce the chance that one exposed password "
            "can unlock several accounts. A password manager can help, and "
            "multifactor authentication adds another layer of protection."
        ),
        "why_wrong": {
            0: "Reusing an exposed password can put multiple accounts at risk.",
            1: "Every account using the reused password should be protected, starting with important accounts.",
            3: "Sharing passwords makes accounts less secure and reduces your control over access.",
        },
    },
    {
        "id": "wifi-01",
        "title": "Public Wi-Fi at a Café",
        "category": "Network Security",
        "difficulty": "Intermediate",
        "story": (
            "You are using public Wi-Fi at a café. A network appears with a name "
            "similar to the café's advertised network. You need to check your "
            "university email."
        ),
        "question": "Which choice is safest?",
        "options": [
            "Connect to whichever network has the strongest signal.",
            "Confirm the correct network with café staff, use HTTPS, and avoid sensitive activity on an untrusted network.",
            "Turn off all device security settings to improve the connection.",
            "Assume every network with the café name is genuine.",
        ],
        "answer": 1,
        "explanation": (
            "Correct. Confirm the network name with staff rather than guessing. "
            "Use secure HTTPS websites, keep your device updated, and avoid "
            "sensitive tasks on networks you do not trust."
        ),
        "why_wrong": {
            0: "Signal strength does not prove that a network is genuine or safe.",
            2: "Turning off security protections makes your device less safe.",
            3: "A similar network name can be misleading. Verify it with the venue.",
        },
    },
    {
        "id": "social-01",
        "title": "The Unexpected Support Call",
        "category": "Social Engineering",
        "difficulty": "Intermediate",
        "story": (
            "Someone calls claiming to be from technical support. They say they "
            "need your one-time login code to stop a security problem. You did "
            "not request support."
        ),
        "question": "What should you do?",
        "options": [
            "Give the code because the caller sounds professional.",
            "Ask the caller to wait while you find your password.",
            "End the call and contact the organization using a trusted number.",
            "Send the code in a text message instead.",
        ],
        "answer": 2,
        "explanation": (
            "Correct. One-time codes are meant for you, not a caller. End unexpected "
            "requests and contact the organization using a number or website you "
            "already trust."
        ),
        "why_wrong": {
            0: "A professional tone does not prove someone's identity. Never share one-time codes.",
            1: "Your password should not be shared with an unexpected caller.",
            3: "Sending the code by text still gives it to the caller.",
        },
    },
    {
        "id": "updates-01",
        "title": "The Delayed Software Update",
        "category": "Device Security",
        "difficulty": "Beginner",
        "story": (
            "Your laptop shows a security update from its normal operating-system "
            "settings. You have postponed it several times because you are busy."
        ),
        "question": "What is a sensible response?",
        "options": [
            "Install the update using the built-in update settings at a suitable time.",
            "Ignore all updates permanently.",
            "Download an update file from a random pop-up advertisement.",
            "Disable security updates to avoid interruptions.",
        ],
        "answer": 0,
        "explanation": (
            "Correct. Security updates often fix known weaknesses. Use the device's "
            "built-in update feature or the vendor's official source, and restart "
            "when it is convenient."
        ),
        "why_wrong": {
            1: "Ignoring security updates can leave known weaknesses unfixed.",
            2: "Random pop-up downloads may be unsafe. Use official update channels.",
            3: "Disabling updates removes an important layer of protection.",
        },
    },
    {
        "id": "backup-01",
        "title": "The Important Coursework File",
        "category": "Data Protection",
        "difficulty": "Intermediate",
        "story": (
            "Your semester project is saved only on your laptop. You realize that "
            "a device problem could make the file unavailable."
        ),
        "question": "What is the best preventive step?",
        "options": [
            "Rename the file several times.",
            "Keep a backup in a separate trusted location and check that it can be restored.",
            "Send the file and your account password to a stranger for safekeeping.",
            "Wait until the laptop stops working before making a copy.",
        ],
        "answer": 1,
        "explanation": (
            "Correct. Keep more than one copy, with at least one backup separate "
            "from your main device. Periodically check that your backup can be "
            "opened or restored."
        ),
        "why_wrong": {
            0: "Renaming a file does not create a backup.",
            2: "Never share account passwords with strangers.",
            3: "A backup is useful when created before a problem occurs.",
        },
    },
]


def get_scenarios(category, difficulty):
    items = SCENARIOS
    if category != "All":
        items = [s for s in items if s["category"] == category]
    if difficulty != "All":
        items = [s for s in items if s["difficulty"] == difficulty]
    return items


# ---------------------------------------------------------
# GROQ AI
# ---------------------------------------------------------
def get_groq_client(api_key):
    if not api_key or Groq is None:
        return None
    return Groq(api_key=api_key)


def ask_ai(client, question, context=""):
    if client is None:
        return None
    prompt = f"""
You are CyberQuest AI, a friendly cybersecurity teacher for beginners.
Explain concepts in simple English. Focus on defensive, legal, ethical safety.
Do not provide instructions for breaking into accounts, stealing credentials,
deploying malware, evading security, or attacking real systems.

Context:
{context}

Student question:
{question}

Give a clear answer with:
1. A short explanation.
2. A simple example.
3. One practical safety tip.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You teach safe, defensive cybersecurity."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=700,
        )
        return response.choices[0].message.content
    except Exception as exc:
        return f"AI request failed: {exc}"


def generate_ai_scenario(client, difficulty, category):
    if client is None:
        return None, "Add your Groq API key in the sidebar to generate an AI scenario."
    prompt = f"""
Create ONE safe, defensive cybersecurity learning scenario.
Difficulty: {difficulty}
Category: {category}
Use a realistic everyday setting such as school, university, home, or a workplace.
The user must choose the safest defensive action. Do not include attack instructions.
Return ONLY valid JSON with these keys:
title, category, difficulty, story, question, options, answer, explanation, why_wrong
Rules:
- options must be a list of exactly four short strings.
- answer must be an integer from 0 to 3.
- why_wrong must be an object with string keys for the three incorrect option indexes.
- Keep the scenario suitable for a beginner cybersecurity learning app.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Return only valid JSON for safe cybersecurity education."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=900,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removesuffix("```").strip()
        data = json.loads(raw)
        if (
            not isinstance(data.get("options"), list)
            or len(data["options"]) != 4
            or data.get("answer") not in [0, 1, 2, 3]
        ):
            raise ValueError("The AI returned an invalid scenario format.")
        data["id"] = "ai-" + str(random.randint(100000, 999999))
        data["category"] = str(data.get("category", category))
        data["difficulty"] = difficulty
        data["why_wrong"] = data.get("why_wrong", {})
        return data, None
    except Exception as exc:
        return None, f"Could not generate a valid scenario: {exc}"


# ---------------------------------------------------------
# CERTIFICATE
# ---------------------------------------------------------
def create_certificate(username, points, accuracy):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setTitle("CyberQuest AI Certificate")
    pdf.setStrokeColorRGB(0.10, 0.40, 0.55)
    pdf.setLineWidth(5)
    pdf.rect(28, 28, width - 56, height - 56)

    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(width / 2, height - 150, "CERTIFICATE")
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawCentredString(width / 2, height - 185, "OF CYBERSECURITY LEARNING")

    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(width / 2, height - 250, "This certificate is presented to")

    pdf.setFont("Helvetica-Bold", 25)
    pdf.drawCentredString(width / 2, height - 300, username)

    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(width / 2, height - 350, "For completing interactive learning activities in")
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawCentredString(width / 2, height - 380, "CyberQuest AI")

    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(width / 2, height - 435, f"Total points: {points}")
    pdf.drawCentredString(width / 2, height - 458, f"Answer accuracy: {accuracy}%")
    pdf.drawCentredString(width / 2, height - 520, f"Date: {datetime.now().strftime('%d %B %Y')}")

    pdf.setFont("Helvetica-Oblique", 10)
    pdf.drawCentredString(width / 2, 75, "An educational achievement certificate — not a professional qualification.")
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


# ---------------------------------------------------------
# SESSION STATE AND SIDEBAR
# ---------------------------------------------------------
init_database()

if "username" not in st.session_state:
    st.session_state.username = "Learner"
if "current_scenario" not in st.session_state:
    st.session_state.current_scenario = None
if "answered_scenarios" not in st.session_state:
    st.session_state.answered_scenarios = set()
if "ai_scenario" not in st.session_state:
    st.session_state.ai_scenario = None

st.sidebar.title("🛡️ CyberQuest AI")
st.sidebar.caption("Learn cybersecurity by making safe decisions.")

username_input = st.sidebar.text_input(
    "Your learner name",
    value=st.session_state.username,
    max_chars=30,
)
clean_name = username_input.strip() or "Learner"
st.session_state.username = clean_name
ensure_user(clean_name)

st.sidebar.divider()
api_key = st.sidebar.text_input(
    "Groq API key (optional)",
    type="password",
    help="Used for the AI Teacher and AI Scenario Generator. Your key is used only for API requests from this app.",
)
if not api_key:
    try:
        api_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        api_key = ""
client = get_groq_client(api_key)

page = st.sidebar.radio(
    "Navigate",
    [
        "🏠 Home",
        "🎮 Missions",
        "🤖 AI Teacher",
        "📊 My Progress",
        "🏆 Achievements",
        "📜 Certificate",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Practice only. Never test security controls on systems you do not own or have permission to assess.")


# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------
if page == "🏠 Home":
    st.markdown(
        """
        <div class="hero">
            <h1>🛡️ CyberQuest AI</h1>
            <p>Learn cybersecurity through interactive, real-world safety decisions.</p>
            <p class="small-muted">Think carefully • Choose safely • Learn something new</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df, stats = get_user_stats(clean_name)
    col1, col2, col3 = st.columns(3)
    col1.metric("Missions completed", stats["attempts"])
    col2.metric("Total XP", stats["points"])
    col3.metric("Accuracy", f'{stats["accuracy"]}%')

    st.subheader("Welcome to your learning journey")
    st.write(
        "CyberQuest AI helps you recognize common digital risks and make safer "
        "choices. Read a situation, choose an action, and learn why it is safe "
        "or risky."
    )

    left, right = st.columns(2)
    with left:
        st.info("🎮 **Missions**\n\nPractice phishing, passwords, public Wi-Fi, social engineering, and more.")
        st.info("🤖 **AI Teacher**\n\nAsk questions and get beginner-friendly cybersecurity explanations.")
    with right:
        st.info("📊 **Progress**\n\nReview your scores, accuracy, and completed learning activities.")
        st.info("🏆 **Achievements**\n\nEarn badges as you complete more missions.")

    st.subheader("How to use CyberQuest")
    st.markdown(
        """
        1. Open **Missions**.
        2. Choose a category and difficulty.
        3. Read the situation and select one answer.
        4. Review the explanation.
        5. Visit **My Progress** to track your learning.
        """
    )
    if not client:
        st.warning("The built-in missions work without an API key. Add a Groq API key in the sidebar to enable AI features.")


# ---------------------------------------------------------
# MISSIONS
# ---------------------------------------------------------
elif page == "🎮 Missions":
    st.title("🎮 Cybersecurity Missions")
    st.write("Choose the safest response to each situation.")

    categories = ["All"] + sorted({s["category"] for s in SCENARIOS})
    category = st.selectbox("Choose a category", categories)
    difficulty = st.selectbox("Choose difficulty", ["All", "Beginner", "Intermediate", "Advanced"])

    available = get_scenarios(category, difficulty)

    with st.expander("✨ Generate an AI mission", expanded=False):
        ai_col1, ai_col2 = st.columns(2)
        with ai_col1:
            ai_difficulty = st.selectbox(
                "AI mission difficulty",
                ["Beginner", "Intermediate", "Advanced"],
                key="ai_difficulty",
            )
        with ai_col2:
            ai_category = st.selectbox(
                "AI mission category",
                ["Phishing", "Password Security", "Network Security", "Social Engineering", "Device Security", "Data Protection"],
                key="ai_category",
            )
        if st.button("Generate AI mission", type="primary"):
            with st.spinner("Creating a safe learning scenario..."):
                generated, error = generate_ai_scenario(client, ai_difficulty, ai_category)
            if error:
                st.error(error)
            else:
                st.session_state.ai_scenario = generated
                st.success("Your AI mission is ready.")

    if st.session_state.ai_scenario:
        available = [st.session_state.ai_scenario] + available

    if not available:
        st.warning("No missions match those filters. Try another difficulty or category.")
    else:
        labels = [f'{s["title"]} — {s["difficulty"]}' for s in available]
        chosen_label = st.selectbox("Select a mission", labels)
        scenario = available[labels.index(chosen_label)]
        st.session_state.current_scenario = scenario

        st.markdown(f"### {scenario['title']}")
        st.caption(f"{scenario['category']} • {scenario['difficulty']}")
        st.info(scenario["story"])
        st.markdown(f"**{scenario['question']}**")

        already_answered = scenario["id"] in st.session_state.answered_scenarios
        if already_answered:
            st.success("You have already completed this mission in this session. Choose another mission to practise.")
        else:
            selected = st.radio(
                "Choose one answer:",
                scenario["options"],
                index=None,
                key=f"answer_{scenario['id']}",
            )
            if st.button("Submit answer", type="primary", disabled=(selected is None)):
                selected_index = scenario["options"].index(selected)
                correct = selected_index == scenario["answer"]
                points = 10 if correct else 2
                save_attempt(clean_name, scenario, selected, correct, points)
                st.session_state.answered_scenarios.add(scenario["id"])
                st.session_state[f"result_{scenario['id']}"] = {
                    "correct": correct,
                    "selected_index": selected_index,
                    "points": points,
                }
                st.rerun()

        result = st.session_state.get(f"result_{scenario['id']}")
        if result:
            if result["correct"]:
                st.success(f"Correct decision! You earned {result['points']} XP.")
            else:
                st.error(f"Not quite. You earned {result['points']} practice XP.")
                wrong_explanation = scenario.get("why_wrong", {}).get(
                    str(result["selected_index"]),
                    scenario.get("why_wrong", {}).get(result["selected_index"], "Review the safer option below."),
                )
                st.write(f"**Why that choice is risky:** {wrong_explanation}")

            st.markdown("**Learning explanation**")
            st.write(scenario["explanation"])
            st.caption("You can repeat this mission after restarting the app session.")


# ---------------------------------------------------------
# AI TEACHER
# ---------------------------------------------------------
elif page == "🤖 AI Teacher":
    st.title("🤖 AI Cyber Teacher")
    st.write("Ask a cybersecurity question and receive a beginner-friendly explanation.")

    starter_questions = [
        "What is phishing?",
        "What is the difference between a threat and a vulnerability?",
        "Why should I use multifactor authentication?",
        "What does a firewall do?",
        "What is the CIA triad?",
    ]
    selected_starter = st.selectbox("Try a sample question", ["Write my own question"] + starter_questions)
    question = st.text_area(
        "Your question",
        value="" if selected_starter == "Write my own question" else selected_starter,
        height=100,
        placeholder="For example: What is a VPN?",
    )

    if st.button("Ask CyberQuest AI", type="primary", disabled=not question.strip()):
        if not client:
            st.warning("Add your Groq API key in the sidebar to use the AI Teacher. You can still use the built-in missions without it.")
        else:
            with st.spinner("The AI teacher is preparing an explanation..."):
                answer = ask_ai(client, question)
            st.markdown("### Explanation")
            st.write(answer)


# ---------------------------------------------------------
# PROGRESS
# ---------------------------------------------------------
elif page == "📊 My Progress":
    st.title("📊 My Learning Progress")
    df, stats = get_user_stats(clean_name)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Missions", stats["attempts"])
    c2.metric("Correct answers", stats["correct"])
    c3.metric("Total XP", stats["points"])
    c4.metric("Accuracy", f'{stats["accuracy"]}%')

    if df.empty:
        st.info("You have not completed a mission yet. Go to Missions to begin.")
    else:
        st.subheader("Performance by category")
        category_df = (
            df.groupby("category", as_index=False)
            .agg(Attempts=("id", "count"), Correct=("correct", "sum"), XP=("points", "sum"))
        )
        fig = px.bar(category_df, x="category", y="Attempts", color="Correct", title="Your mission activity")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Recent activity")
        display_df = df[["scenario_title", "category", "difficulty", "correct", "points", "completed_at"]].copy()
        display_df["correct"] = display_df["correct"].map({1: "Yes", 0: "Not yet"})
        display_df.columns = ["Mission", "Category", "Difficulty", "Correct?", "XP", "Completed at"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download my learning history (CSV)",
            data=csv,
            file_name="cyberquest_learning_history.csv",
            mime="text/csv",
        )


# ---------------------------------------------------------
# ACHIEVEMENTS
# ---------------------------------------------------------
elif page == "🏆 Achievements":
    st.title("🏆 Your Achievements")
    df, stats = get_user_stats(clean_name)

    badges = [
        ("🌱 First Steps", stats["attempts"] >= 1, "Complete your first mission."),
        ("🧭 Curious Learner", stats["attempts"] >= 5, "Complete five missions."),
        ("⭐ XP Collector", stats["points"] >= 40, "Earn at least 40 XP."),
        ("🎯 Careful Thinker", stats["accuracy"] >= 80 and stats["attempts"] >= 5, "Reach 80% accuracy after five missions."),
        ("🛡️ Cyber Defender", stats["attempts"] >= 10, "Complete ten missions."),
    ]

    st.metric("Badges unlocked", sum(1 for _, unlocked, _ in badges if unlocked))
    for name, unlocked, description in badges:
        if unlocked:
            st.success(f"{name} — {description}")
        else:
            st.info(f"🔒 {name} — {description}")


# ---------------------------------------------------------
# CERTIFICATE
# ---------------------------------------------------------
elif page == "📜 Certificate":
    st.title("📜 Learning Certificate")
    df, stats = get_user_stats(clean_name)

    st.write(
        "You can create an educational completion certificate after completing "
        "at least five missions. This certificate recognizes app activity; it is "
        "not a professional cybersecurity qualification."
    )

    if stats["attempts"] < 5:
        st.warning(f"Complete {5 - stats['attempts']} more mission(s) to unlock your certificate.")
    else:
        st.success("Your learning certificate is ready.")
        pdf_data = create_certificate(clean_name, stats["points"], stats["accuracy"])
        st.download_button(
            "Download certificate (PDF)",
            data=pdf_data,
            file_name="CyberQuest_AI_Certificate.pdf",
            mime="application/pdf",
            type="primary",
        )

st.divider()
st.caption("CyberQuest AI • Educational cybersecurity simulator • Learn safely and ethically.")
