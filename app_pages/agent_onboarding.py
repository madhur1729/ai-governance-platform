import streamlit as st
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from onboarding_scorer import OnboardingScorer, VersionManager
from audit_logger import AuditLogger
import json

def show():
    st.title("📋 Agent Onboarding & Risk Assessment")

    st.markdown("""
    This page demonstrates:
    1. **Agent Registration** - Define tools and data access
    2. **Automated Checklist** - Validate against governance rules
    3. **Risk Scoring** - Compute risk tier (LOW/MEDIUM/HIGH)
    4. **Version Management** - Track changes and trigger re-review
    """)

    # Initialize scorer and version manager
    if st.session_state.get("scorer") is None:
        st.session_state.scorer = OnboardingScorer("config/checklist_rules.yaml")
        st.session_state.version_manager = VersionManager()

    # Tab selection
    tab1, tab2 = st.tabs(["📋 Register Agent", "📊 Agent Registry"])

    with tab1:
        st.subheader("Register New Agent")

        col1, col2 = st.columns(2)

        with col1:
            agent_name = st.text_input(
                "Agent Name",
                value="HR Assistant",
                help="Unique identifier for the agent"
            )

            use_case = st.text_area(
                "Use Case Description",
                value="Handles employee queries about HR policies, PTO, benefits, and salary information",
                help="What will this agent do?"
            )

        with col2:
            st.write("**Available Tools**")
            tools = st.multiselect(
                "Select tools this agent can access:",
                ["lookup_employee", "update_pto_balance", "send_email", "get_pto_policy", "query_benefits"],
                default=["lookup_employee", "update_pto_balance", "send_email"],
                key="tools_select"
            )

            st.write("**Data Access**")
            data_types = st.multiselect(
                "Data this agent will access:",
                ["PII", "internal", "public"],
                default=["PII", "internal"],
                key="data_select"
            )

        st.markdown("---")

        if st.button("🚀 Register & Score Agent", use_container_width=True, type="primary"):
            if not agent_name.strip():
                st.error("Agent name is required")
            else:
                # Prepare agent config
                agent_config = {
                    "name": agent_name,
                    "use_case": use_case,
                    "tools": tools,
                    "data_accessed": data_types
                }

                with st.spinner("Analyzing agent..."):
                    # Score the agent
                    scorer = st.session_state.scorer
                    risk_assessment = scorer.compute_risk_score(agent_config)

                    # Register version
                    version = st.session_state.version_manager.register_version(agent_name, agent_config)

                    # Log event
                    logger = AuditLogger()
                    event_id = logger.log_onboarding(agent_name, risk_assessment)

                    # Store in session
                    st.session_state.agents[agent_name] = {
                        "config": agent_config,
                        "risk_assessment": risk_assessment,
                        "version": version,
                        "status": "ESCALATED" if risk_assessment.get("requires_human_review") else "AUTO_APPROVED"
                    }

                    st.session_state.audit_log.append({
                        "event_id": event_id,
                        "timestamp": __import__('datetime').datetime.now().isoformat(),
                        "event_type": "onboarding",
                        "agent_name": agent_name,
                        "action": "register_agent",
                        "result": risk_assessment.get("status", "ESCALATED"),
                        "risk_score": risk_assessment.get("risk_score", 0),
                        "details": {
                            "risk_tier": risk_assessment.get("risk_tier"),
                            "tools": len(tools),
                            "data_accessed": data_types
                        }
                    })

                # Display results
                st.success("✅ Agent registration complete!")

                st.subheader("🎯 Risk Assessment Results")

                col1, col2, col3 = st.columns(3)

                risk_tier = risk_assessment.get("risk_tier", "UNKNOWN")
                risk_color_map = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}

                with col1:
                    st.metric("Risk Tier", f"{risk_color_map.get(risk_tier, '⚪')} {risk_tier}")

                with col2:
                    st.metric("Risk Score", f"{risk_assessment.get('risk_score', 0):.1f}/100")

                with col3:
                    auto_approve = risk_assessment.get("auto_approve", False)
                    status = "✅ Auto-Approved" if auto_approve else "⚠️ Escalation Needed"
                    st.metric("Status", status)

                st.markdown("---")

                st.subheader("📋 Compliance Checklist")

                checklist = risk_assessment.get("checklist", {})
                for check_id, check_info in checklist.items():
                    status_icon = check_info["status"]

                    with st.expander(f"{status_icon} {check_info['name']}"):
                        st.write(f"**Score**: {check_info['score']}/100 (weight: {check_info['weight']}%)")
                        st.write(f"**Message**: {check_info['message']}")

                if risk_assessment.get("escalation_reason"):
                    st.warning(f"**Escalation Reason**: {risk_assessment['escalation_reason']}")
                else:
                    st.success("**All checks passed - agent approved for deployment**")

    with tab2:
        st.subheader("Registered Agents")

        if not st.session_state.agents:
            st.info("No agents registered yet. Register one on the 'Register Agent' tab.")
        else:
            for agent_name, agent_data in st.session_state.agents.items():
                with st.expander(f"🤖 {agent_name}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        config = agent_data.get("config", {})
                        st.write(f"**Use Case**: {config.get('use_case', 'N/A')}")
                        st.write(f"**Tools**: {', '.join(config.get('tools', []))}")
                        st.write(f"**Data Access**: {', '.join(config.get('data_accessed', []))}")

                    with col2:
                        risk_assessment = agent_data.get("risk_assessment", {})
                        risk_tier = risk_assessment.get("risk_tier", "UNKNOWN")
                        risk_color_map = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}

                        st.write(f"**Risk Tier**: {risk_color_map.get(risk_tier, '⚪')} {risk_tier}")
                        st.write(f"**Risk Score**: {risk_assessment.get('risk_score', 0):.1f}/100")
                        st.write(f"**Status**: {agent_data.get('status', 'UNKNOWN')}")

                    # Version history
                    st.subheader("📜 Version History")

                    version = agent_data.get("version", {})
                    st.write(f"**Current Version**: {version.get('version_id', 'v1')}")
                    st.write(f"**Timestamp**: {version.get('timestamp', 'N/A')}")

                    # Detect changes
                    with st.expander("🔄 Check for Changes"):
                        new_config = config.copy()
                        change_detection = st.session_state.version_manager.detect_changes(agent_name, new_config)

                        if change_detection.get("changed"):
                            st.warning("⚠️ Configuration has changed")
                            st.write(f"**Reason**: {change_detection.get('reason')}")
                            st.write("**Changes Detected**:")
                            for change in change_detection.get("changes", []):
                                st.write(f"- {change}")
                        else:
                            st.success("✅ No changes detected")

                    # Approval button
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("✅ Approve", key=f"approve_{agent_name}"):
                            st.success(f"✅ {agent_name} approved for deployment")

                    with col2:
                        if st.button("❌ Reject", key=f"reject_{agent_name}"):
                            st.error(f"❌ {agent_name} rejected")

                    with col3:
                        if st.button("🔄 Revisit", key=f"revisit_{agent_name}"):
                            st.info("Marked for re-review")
