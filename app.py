import os
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from dotenv import load_dotenv
from openai import OpenAI
from sklearn.ensemble import IsolationForest


# =====================================================
# 1. PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="TheGuard AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =====================================================
# 2. ENVIRONMENT VARIABLES
# =====================================================
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


# =====================================================
# 3. CUSTOM DASHBOARD STYLING
# =====================================================
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0B1120;
        color: #F9FAFB;
    }

    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #263244;
    }

    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #E5E7EB;
    }

    [data-testid="stMetric"] {
        background-color: #111827;
        border: 1px solid #263244;
        padding: 18px;
        border-radius: 12px;
    }

    [data-testid="stMetricLabel"] {
        color: #9CA3AF;
    }

    [data-testid="stMetricValue"] {
        color: #F9FAFB;
    }

    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        min-height: 42px;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    hr {
        border-color: #263244;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =====================================================
# 4. SESSION STATE
# =====================================================
if "login_data" not in st.session_state:
    st.session_state.login_data = None

if "result" not in st.session_state:
    st.session_state.result = None

if "ai_explanation" not in st.session_state:
    st.session_state.ai_explanation = None

if "history" not in st.session_state:
    st.session_state.history = []


# =====================================================
# 5. MACHINE LEARNING MODEL
# =====================================================
@st.cache_resource
def train_model():
    np.random.seed(42)

    normal_data = pd.DataFrame(
        {
            "failed_attempts": np.random.randint(0, 3, 1000),
            "new_device": np.random.randint(0, 2, 1000),
            "unfamiliar_country": np.random.choice(
                [0, 1], 1000, p=[0.95, 0.05]
            ),
            "unusual_time": np.random.choice(
                [0, 1], 1000, p=[0.8, 0.2]
            ),
            "ip_risk": np.random.uniform(0, 0.4, 1000),
            "impossible_travel": np.random.choice(
                [0, 1], 1000, p=[0.98, 0.02]
            ),
        }
    )

    model = IsolationForest(
        contamination=0.05,
        random_state=42,
    )
    model.fit(normal_data)
    return model


model = train_model()


# =====================================================
# 6. LOGIN RISK ANALYSIS
# =====================================================
def analyze_login(login_data):
    features = pd.DataFrame(
        [
            {
                "failed_attempts": login_data["failed_attempts"],
                "new_device": int(login_data["new_device"]),
                "unfamiliar_country": int(login_data["unfamiliar_country"]),
                "unusual_time": int(login_data["unusual_time"]),
                "ip_risk": login_data["ip_risk"],
                "impossible_travel": int(login_data["impossible_travel"]),
            }
        ]
    )

    prediction = model.predict(features)[0]
    is_anomaly = prediction == -1

    risk_factors = {
        "Failed Attempts": min(login_data["failed_attempts"] * 5, 20),
        "New Device": 15 if login_data["new_device"] else 0,
        "Unfamiliar Country": 20 if login_data["unfamiliar_country"] else 0,
        "Unusual Time": 10 if login_data["unusual_time"] else 0,
        "IP Risk": login_data["ip_risk"] * 20,
        "Impossible Travel": 20 if login_data["impossible_travel"] else 0,
        "ML Anomaly": 7 if is_anomaly else 0,
    }

    risk_score = min(round(sum(risk_factors.values())), 100)

    if risk_score < 30:
        risk_level = "Low"
        action = "Allow login"
    elif risk_score < 65:
        risk_level = "Medium"
        action = "Require additional verification"
    else:
        risk_level = "High"
        action = "Block login and alert user"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "is_anomaly": is_anomaly,
        "action": action,
        "risk_factors": risk_factors,
    }


# =====================================================
# 7. GROQ AI SECURITY EXPLANATION
# =====================================================
def explain_risk(login_data, result):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        try:
            api_key = st.secrets["GROQ_API_KEY"]
        except (KeyError, FileNotFoundError):
            api_key = None

    prompt = f"""
You are a professional cybersecurity analyst working for TheGuard AI.

Analyze this simulated login activity.

LOGIN DETAILS:
{login_data}

RISK SCORE: {result['risk_score']}/100
RISK LEVEL: {result['risk_level']}
ML ANOMALY: {result['is_anomaly']}
RECOMMENDED ACTION: {result['action']}
RISK FACTORS: {result['risk_factors']}

Generate a professional security report using these sections:
1. SECURITY ANALYSIS
2. DETECTED THREATS
3. WHY THIS RISK SCORE?
4. RECOMMENDED SECURITY ACTION
5. SECURITY ADVICE

IMPORTANT:
- Do not change the calculated risk score or recommended action.
- Do not claim the account was definitely hacked.
- Do not invent IP addresses or login information.
- Distinguish ML anomaly detection from rule-based scoring.
- This is simulated login data.
- Keep the report clear and professional.
"""

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=45.0,
        )

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are TheGuard AI, a professional "
                        "cybersecurity explanation assistant."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=1200,
        )

        explanation = response.choices[0].message.content
        return explanation or "Groq returned an empty response."

    except Exception as error:
        return f"Groq API error: {str(error)}"


# =====================================================
# 8. SIDEBAR NAVIGATION
# =====================================================
st.sidebar.title("🛡️ TheGuard AI")
st.sidebar.caption("Account Security Platform")
st.sidebar.divider()

selected_page = st.sidebar.radio(
    "NAVIGATION",
    ["Dashboard", "Login Analysis", "Security History", "About"],
    index=0,
)

st.sidebar.divider()


# =====================================================
# 9. DASHBOARD PAGE
# =====================================================
if selected_page == "Dashboard":
    st.title("🛡️ TheGuard AI")
    st.subheader("Security Dashboard")
    st.write(
        "Monitor simulated login activity and review account takeover risk."
    )
    st.divider()

    total_checks = len(st.session_state.history)
    high_risk_checks = sum(
        1 for item in st.session_state.history if item["Risk Level"] == "High"
    )
    medium_risk_checks = sum(
        1 for item in st.session_state.history if item["Risk Level"] == "Medium"
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Login Analyses", total_checks)
    col2.metric("High-Risk Results", high_risk_checks)
    col3.metric("Medium-Risk Results", medium_risk_checks)

    st.divider()
    st.subheader("Recent Security Activity")

    if st.session_state.history:
        recent_df = pd.DataFrame(st.session_state.history).tail(5)
        st.dataframe(recent_df, use_container_width=True, hide_index=True)
    else:
        st.info(
            "No login analyses yet. Open Login Analysis in the sidebar "
            "to run your first security check."
        )

    st.stop()


# =====================================================
# 10. SECURITY HISTORY PAGE
# =====================================================
if selected_page == "Security History":
    st.title("📜 Security History")
    st.write("Review login analyses completed during this app session.")
    st.divider()

    if st.session_state.history:
        history_df = pd.DataFrame(st.session_state.history)
        st.dataframe(history_df, use_container_width=True, hide_index=True)

        csv_data = history_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Security History (CSV)",
            data=csv_data,
            file_name="theguard_security_history.csv",
            mime="text/csv",
        )
    else:
        st.info("No security history is available yet. Run a login analysis first.")

    st.caption(
        "History is stored in Streamlit session state and may be cleared "
        "when the session resets. It is not permanent database storage."
    )
    st.stop()


# =====================================================
# 11. ABOUT PAGE
# =====================================================
if selected_page == "About":
    st.title("ℹ️ About TheGuard AI")
    st.subheader("AI-Powered Account Takeover Detection Prototype")
    st.write(
        "TheGuard AI is a prototype that evaluates simulated login "
        "behaviour using rule-based risk scoring and an Isolation Forest "
        "anomaly detector. Groq AI can explain the calculated result and "
        "provide security recommendations."
    )

    st.subheader("Technology Stack")
    st.markdown(
        """
        - **Python** — application logic
        - **Streamlit** — interactive dashboard
        - **Pandas and NumPy** — data handling
        - **Scikit-learn** — Isolation Forest anomaly detection
        - **Plotly** — risk-factor visualization
        - **Groq API** — AI-generated security explanation
        """
    )

    st.warning(
        "This is a hackathon/learning prototype using simulated login data. "
        "It does not connect to PayPal, real user accounts, or private "
        "authentication systems. Its output should not be used as the sole "
        "basis for real security decisions."
    )
    st.stop()


# =====================================================
# 12. LOGIN ANALYSIS PAGE - SIDEBAR INPUTS
# =====================================================
st.sidebar.subheader("🔐 Login Activity")
st.sidebar.write("Enter login activity details to analyze account risk.")

failed_attempts = st.sidebar.slider(
    "Failed Login Attempts",
    min_value=0,
    max_value=10,
    value=0,
)

new_device = st.sidebar.selectbox(
    "Login From New Device?",
    ["No", "Yes"],
)

unfamiliar_country = st.sidebar.selectbox(
    "Login From Unfamiliar Country?",
    ["No", "Yes"],
)

unusual_time = st.sidebar.selectbox(
    "Login At Unusual Time?",
    ["No", "Yes"],
)

ip_risk = st.sidebar.slider(
    "IP Risk Score",
    min_value=0.0,
    max_value=1.0,
    value=0.1,
    step=0.05,
)

impossible_travel = st.sidebar.selectbox(
    "Impossible Travel Detected?",
    ["No", "Yes"],
)

st.sidebar.divider()
analyze_button = st.sidebar.button(
    "🔍 Analyze Login",
    type="primary",
    use_container_width=True,
)


# =====================================================
# 13. RUN LOGIN ANALYSIS
# =====================================================
if analyze_button:
    login_data = {
        "failed_attempts": failed_attempts,
        "new_device": new_device == "Yes",
        "unfamiliar_country": unfamiliar_country == "Yes",
        "unusual_time": unusual_time == "Yes",
        "ip_risk": ip_risk,
        "impossible_travel": impossible_travel == "Yes",
    }

    result = analyze_login(login_data)

    st.session_state.login_data = login_data
    st.session_state.result = result
    st.session_state.ai_explanation = None

    st.session_state.history.append(
        {
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Risk Score": result["risk_score"],
            "Risk Level": result["risk_level"],
            "ML Anomaly": "Detected" if result["is_anomaly"] else "Normal",
            "Recommended Action": result["action"],
        }
    )


# =====================================================
# 14. LOGIN ANALYSIS PAGE CONTENT
# =====================================================
st.title("🛡️ TheGuard AI")
st.subheader("AI-Powered Account Takeover Detection System")
st.write(
    "TheGuard AI analyzes login behaviour using Machine Learning "
    "and rule-based risk scoring to identify potentially suspicious "
    "account access attempts."
)
st.divider()

if st.session_state.result is not None:
    result = st.session_state.result
    login_data = st.session_state.login_data

    st.header("📊 Login Risk Analysis")

    col1, col2, col3 = st.columns(3)
    col1.metric("Risk Score", f"{result['risk_score']}/100")
    col2.metric("Risk Level", result["risk_level"])
    col3.metric(
        "ML Anomaly",
        "Detected" if result["is_anomaly"] else "Normal",
    )

    st.subheader("Risk Score Indicator")
    st.progress(result["risk_score"] / 100)

    if result["risk_level"] == "Low":
        st.success("🟢 LOW RISK — " + result["action"])
    elif result["risk_level"] == "Medium":
        st.warning("🟠 MEDIUM RISK — " + result["action"])
    else:
        st.error("🔴 HIGH RISK — " + result["action"])

    st.divider()
    st.header("🔎 Login Behaviour Indicators")

    indicator_col1, indicator_col2 = st.columns(2)
    with indicator_col1:
        st.write("**Failed Attempts:**", login_data["failed_attempts"])
        st.write("**New Device:**", "Yes" if login_data["new_device"] else "No")
        st.write(
            "**Unfamiliar Country:**",
            "Yes" if login_data["unfamiliar_country"] else "No",
        )

    with indicator_col2:
        st.write("**Unusual Time:**", "Yes" if login_data["unusual_time"] else "No")
        st.write("**IP Risk:**", login_data["ip_risk"])
        st.write(
            "**Impossible Travel:**",
            "Yes" if login_data["impossible_travel"] else "No",
        )

    st.divider()
    st.header("📈 Risk Factor Breakdown")

    chart_data = pd.DataFrame(
        {
            "Risk Factor": list(result["risk_factors"].keys()),
            "Contribution": list(result["risk_factors"].values()),
        }
    )

    fig = px.bar(
        chart_data,
        x="Contribution",
        y="Risk Factor",
        orientation="h",
        title="Contribution of Each Factor to Risk Score",
        text="Contribution",
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB"),
        xaxis_title="Risk Points",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=10, r=20, t=60, b=20),
    )
    fig.update_traces(marker_color="#3B82F6", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "The chart shows individual contributions before the final score "
        "is capped at 100."
    )

    st.divider()
    st.header("🤖 Groq AI Security Explanation")
    st.write(
        "Ask Groq AI to explain the detected login activity and provide "
        "security recommendations."
    )

    if st.button("✨ Explain with Groq AI", type="primary"):
        with st.spinner("Groq AI is analysing the login..."):
            st.session_state.ai_explanation = explain_risk(login_data, result)

    if st.session_state.ai_explanation:
        st.subheader("📝 AI Security Report")
        st.markdown(st.session_state.ai_explanation)

else:
    st.info(
        "👈 Enter login activity details in the sidebar and click "
        "Analyze Login to get started."
    )
    st.subheader("Welcome to TheGuard AI")
    st.write(
        "Your account security monitoring dashboard is ready to analyze "
        "simulated login activity."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Risk Score", "--")
    col2.metric("Risk Level", "Waiting")
    col3.metric("ML Anomaly", "Waiting")


# =====================================================
# 15. FOOTER
# =====================================================
st.divider()
st.caption(
    "TheGuard AI | AI-Powered Account Takeover Detection"
)

