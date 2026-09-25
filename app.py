import streamlit as st
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure page FIRST
st.set_page_config(
    page_title="AI Governance Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize ALL session state at the very top (before any widgets)
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []
if "agents" not in st.session_state:
    st.session_state.agents = {}
if "violations" not in st.session_state:
    st.session_state.violations = []
if "page_nav" not in st.session_state:
    st.session_state.page_nav = "🏠 Dashboard"
if "run_query" not in st.session_state:
    st.session_state.run_query = False
if "retriever" not in st.session_state:
    st.session_state.retriever = None
if "scorer" not in st.session_state:
    st.session_state.scorer = None
if "version_manager" not in st.session_state:
    st.session_state.version_manager = None

# Sidebar navigation
st.sidebar.title("🛡️ AI Governance Platform")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "💬 Injection Detection",
        "📚 RAG Validation",
        "📋 Agent Onboarding",
        "📊 Audit & Reports"
    ],
    key="page_nav"
)

st.sidebar.markdown("---")
st.sidebar.info(
    """
    **About this demo:**

    This platform demonstrates real-time governance and compliance monitoring for enterprise AI systems.

    - **Injection Detection**: Tests prompts for injection attacks
    - **RAG Validation**: Validates retrieved content and responses
    - **Onboarding**: Automated risk scoring for new agents
    - **Audit Trail**: Comprehensive logging and reporting
    """
)

# Page routing
if page == "🏠 Dashboard":
    from app_pages import dashboard
    dashboard.show()

elif page == "💬 Injection Detection":
    from app_pages import injection_detection
    injection_detection.show()

elif page == "📚 RAG Validation":
    from app_pages import rag_validation
    rag_validation.show()

elif page == "📋 Agent Onboarding":
    from app_pages import agent_onboarding
    agent_onboarding.show()

elif page == "📊 Audit & Reports":
    from app_pages import audit_reports
    audit_reports.show()
