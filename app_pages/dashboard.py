import streamlit as st
from datetime import datetime

def show():
    st.title("🏠 Governance Dashboard")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Events Logged", len(st.session_state.audit_log))

    with col2:
        violations = len(st.session_state.violations)
        st.metric("Active Violations", violations)

    with col3:
        agents = len(st.session_state.agents)
        st.metric("Registered Agents", agents)

    st.markdown("---")

    st.subheader("📋 Quick Overview")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Recent Events")
        if st.session_state.audit_log:
            for event in st.session_state.audit_log[-10:]:
                timestamp = event.get("timestamp", "")
                agent = event.get("agent_name", "Unknown")
                result = event.get("result", "")
                color_map = {
                    "ALLOWED": "🟢",
                    "BLOCKED": "🔴",
                    "ESCALATED": "🟡",
                    "REDACTED": "🟡",
                    "APPROVED": "🟢",
                    "REJECTED": "🔴"
                }
                icon = color_map.get(result, "⚪")
                st.write(f"{icon} **{agent}** - {result} ({timestamp[-8:]})")
        else:
            st.info("No events logged yet. Start using the platform!")

    with col2:
        st.subheader("Risk Distribution")
        if st.session_state.agents:
            risk_tiers = {}
            for agent_name, agent_data in st.session_state.agents.items():
                tier = agent_data.get("risk_tier", "UNKNOWN")
                risk_tiers[tier] = risk_tiers.get(tier, 0) + 1

            for tier in ["LOW", "MEDIUM", "HIGH"]:
                count = risk_tiers.get(tier, 0)
                if count > 0:
                    st.write(f"**{tier}**: {count} agent(s)")
        else:
            st.info("Register agents to see risk distribution")

    st.markdown("---")

    st.subheader("🚨 Violations Summary")
    if st.session_state.violations:
        for violation in st.session_state.violations[-5:]:
            with st.expander(f"⚠️ {violation.get('agent_name')} - {violation.get('result')}"):
                st.write(f"**Type**: {violation.get('event_type')}")
                st.write(f"**Risk Score**: {violation.get('risk_score', 0):.2f}")
                st.write(f"**Details**: {violation.get('details', {})}")
    else:
        st.success("✅ No violations recorded!")

    st.markdown("---")

    st.subheader("📊 Next Steps")
    st.markdown("""
    1. **Try Injection Detection** - Test the chatbot with attack prompts
    2. **RAG Validation** - Query the knowledge base and see response validation
    3. **Register Agents** - Add agents and see risk scoring
    4. **Review Audit Trail** - Generate governance reports
    """)
