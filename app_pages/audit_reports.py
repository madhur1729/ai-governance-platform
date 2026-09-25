import streamlit as st
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from report_generator import HTMLReportGenerator, ReportExporter
from audit_logger import AuditLogger
import json
from datetime import datetime

def show():
    st.title("📊 Audit Trail & Reports")

    st.markdown("""
    This page provides:
    1. **Audit Log** - All governance events with details
    2. **Violations** - Flagged security and compliance issues
    3. **Report Generation** - HTML reports for stakeholders
    4. **Statistics** - Governance metrics and trends
    """)

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 Audit Log", "📈 Statistics", "📄 Generate Report"])

    with tab1:
        st.subheader("Complete Audit Log")

        # Filter options
        col1, col2, col3 = st.columns(3)

        with col1:
            filter_agent = st.selectbox(
                "Filter by Agent:",
                ["All Agents"] + list(set(e.get("agent_name", "Unknown") for e in st.session_state.audit_log))
            )

        with col2:
            filter_type = st.selectbox(
                "Filter by Type:",
                ["All Types", "injection_detection", "rag_validation", "onboarding", "audit"]
            )

        with col3:
            filter_result = st.selectbox(
                "Filter by Result:",
                ["All Results", "ALLOWED", "BLOCKED", "ESCALATED", "REDACTED", "APPROVED", "REJECTED"]
            )

        # Apply filters
        filtered_events = st.session_state.audit_log

        if filter_agent != "All Agents":
            filtered_events = [e for e in filtered_events if e.get("agent_name") == filter_agent]

        if filter_type != "All Types":
            filtered_events = [e for e in filtered_events if e.get("event_type") == filter_type]

        if filter_result != "All Results":
            filtered_events = [e for e in filtered_events if e.get("result") == filter_result]

        st.write(f"**Showing {len(filtered_events)} events**")

        if not filtered_events:
            st.info("No matching events found")
        else:
            # Display as table
            for event in reversed(filtered_events[-50:]):  # Show last 50
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.caption(event.get("timestamp", "")[-8:])

                with col2:
                    st.write(f"**{event.get('agent_name', 'Unknown')}**")

                with col3:
                    event_type = event.get("event_type", "unknown")
                    st.caption(event_type)

                with col4:
                    result = event.get("result", "")
                    color_map = {
                        "ALLOWED": "🟢",
                        "BLOCKED": "🔴",
                        "ESCALATED": "🟡",
                        "REDACTED": "🟡",
                        "APPROVED": "🟢",
                        "REJECTED": "🔴",
                        "FOUND_ISSUES": "🔴",
                        "PASSED": "🟢"
                    }
                    icon = color_map.get(result, "⚪")
                    st.write(f"{icon} {result}")

                with st.expander("📝 Details"):
                    st.json({
                        "timestamp": event.get("timestamp"),
                        "event_id": event.get("event_id"),
                        "action": event.get("action"),
                        "risk_score": event.get("risk_score"),
                        "details": event.get("details")
                    })

    with tab2:
        st.subheader("Governance Statistics")

        # Get stats
        if not st.session_state.audit_log:
            st.info("No events logged yet")
        else:
            # Overall stats
            col1, col2, col3, col4 = st.columns(4)

            total_events = len(st.session_state.audit_log)
            violations = len(st.session_state.violations)

            with col1:
                st.metric("Total Events", total_events)

            with col2:
                st.metric("Violations", violations)

            with col3:
                if total_events > 0:
                    violation_rate = (violations / total_events) * 100
                    st.metric("Violation Rate", f"{violation_rate:.1f}%")
                else:
                    st.metric("Violation Rate", "0%")

            with col4:
                unique_agents = len(set(e.get("agent_name") for e in st.session_state.audit_log))
                st.metric("Unique Agents", unique_agents)

            st.markdown("---")

            # Event type breakdown
            st.subheader("Events by Type")
            event_types = {}
            for event in st.session_state.audit_log:
                et = event.get("event_type", "unknown")
                event_types[et] = event_types.get(et, 0) + 1

            col1, col2 = st.columns(2)

            with col1:
                st.bar_chart(event_types)

            with col2:
                st.write("**Breakdown**:")
                for et, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
                    st.write(f"- **{et}**: {count} events")

            st.markdown("---")

            # Results breakdown
            st.subheader("Results Distribution")
            results = {}
            for event in st.session_state.audit_log:
                result = event.get("result", "unknown")
                results[result] = results.get(result, 0) + 1

            col1, col2 = st.columns(2)

            with col1:
                st.bar_chart(results)

            with col2:
                st.write("**Summary**:")
                for result, count in sorted(results.items(), key=lambda x: x[1], reverse=True):
                    st.write(f"- **{result}**: {count} ({count/total_events*100:.1f}%)")

            st.markdown("---")

            # Top agents
            st.subheader("Agents with Most Activity")
            agent_counts = {}
            for event in st.session_state.audit_log:
                agent = event.get("agent_name", "Unknown")
                agent_counts[agent] = agent_counts.get(agent, 0) + 1

            for agent, count in sorted(agent_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{agent}**")
                with col2:
                    st.metric("Events", count)

    with tab3:
        st.subheader("Generate Governance Report")

        col1, col2 = st.columns(2)

        with col1:
            report_title = st.text_input(
                "Report Title",
                value="AI Governance Audit Report",
                help="Title for the HTML report"
            )

        with col2:
            include_details = st.checkbox("Include detailed event logs", value=True)

        if st.button("📄 Generate HTML Report", use_container_width=True, type="primary"):
            with st.spinner("Generating report..."):
                # Prepare data
                logger = AuditLogger()

                # Create report data
                report_data = {
                    "events": st.session_state.audit_log,
                    "violations": st.session_state.violations,
                    "approvals": [e for e in st.session_state.audit_log if e.get("result") in ["APPROVED", "AUTO_APPROVED"]],
                    "stats": {
                        "total_events": len(st.session_state.audit_log),
                        "total_violations": len(st.session_state.violations),
                        "violation_rate": len(st.session_state.violations) / len(st.session_state.audit_log) if st.session_state.audit_log else 0,
                        "event_types": {},
                        "results": {},
                        "unique_agents": len(set(e.get("agent_name") for e in st.session_state.audit_log)),
                        "agents": list(set(e.get("agent_name") for e in st.session_state.audit_log)),
                        "avg_risk_score": sum(e.get("risk_score", 0) for e in st.session_state.audit_log) / len(st.session_state.audit_log) if st.session_state.audit_log else 0
                    },
                    "timestamp": datetime.now().isoformat()
                }

                # Count event types and results
                for event in st.session_state.audit_log:
                    et = event.get("event_type", "unknown")
                    report_data["stats"]["event_types"][et] = report_data["stats"]["event_types"].get(et, 0) + 1

                    result = event.get("result", "unknown")
                    report_data["stats"]["results"][result] = report_data["stats"]["results"].get(result, 0) + 1

                # Generate HTML
                generator = HTMLReportGenerator()
                html_content = generator.generate_report(report_data, report_title)

                # Save to file
                filename = f"governance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                ReportExporter.save_html(html_content, filename)

                # Display download button
                st.success(f"✅ Report generated: {filename}")

                with open(filename, 'r', encoding='utf-8') as f:
                    st.download_button(
                        label="📥 Download HTML Report",
                        data=f.read(),
                        file_name=filename,
                        mime="text/html"
                    )

                # Show preview
                st.subheader("📋 Report Preview")
                with st.expander("View HTML Report (first 2000 chars)"):
                    st.code(html_content[:2000] + "...", language="html")

        st.markdown("---")

        st.subheader("📊 Export Data")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📥 Download JSON", use_container_width=True):
                json_data = json.dumps({
                    "events": st.session_state.audit_log,
                    "violations": st.session_state.violations,
                    "agents": st.session_state.agents
                }, indent=2, default=str)

                st.download_button(
                    label="📥 Download JSON",
                    data=json_data,
                    file_name=f"governance_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )

        with col2:
            if st.button("📋 Copy as CSV", use_container_width=True):
                # Create CSV from events
                csv_data = "timestamp,agent,event_type,action,result,risk_score\n"
                for event in st.session_state.audit_log:
                    csv_data += f"{event.get('timestamp','')},{event.get('agent_name','')},{event.get('event_type','')},{event.get('action','')},{event.get('result','')},{event.get('risk_score','')}\n"

                st.download_button(
                    label="📋 Download CSV",
                    data=csv_data,
                    file_name=f"governance_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
