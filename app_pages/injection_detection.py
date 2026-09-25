import streamlit as st
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from injection_detector import detect_prompt_injection
from audit_logger import AuditLogger
import yaml

def load_attack_scenarios():
    """Load attack scenarios from config"""
    try:
        with open("config/attack_prompts.yaml", 'r') as f:
            config = yaml.safe_load(f)
            return config.get("attack_scenarios", [])
    except:
        return []

def show():
    st.title("💬 Prompt Injection Detection")

    st.markdown("""
    This page demonstrates real-time detection of prompt injection attacks using a three-tier approach:
    1. **Heuristic** (fast, pattern-based)
    2. **Semantic** (similarity-based)
    3. **LLM-Judge** (Claude-based reasoning)
    """)

    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("Test Prompts")
        attack_scenarios = load_attack_scenarios()

        # Dropdown for predefined attacks
        attack_options = {s["id"]: f"{s['category'].upper()} - {s['description']}" for s in attack_scenarios}
        selected_attack = st.selectbox("Or use a predefined attack:", list(attack_options.keys()) + ["custom"])

        if selected_attack == "custom":
            user_prompt = st.text_area(
                "Enter your prompt to test:",
                height=100,
                placeholder="Type a prompt here..."
            )
        else:
            selected_scenario = next((s for s in attack_scenarios if s["id"] == selected_attack), None)
            user_prompt = st.text_area(
                "Prompt to analyze:",
                value=selected_scenario["prompt"] if selected_scenario else "",
                height=100,
                disabled=True
            )

    with col2:
        risk_tier = st.selectbox(
            "Agent Risk Tier",
            ["LOW", "MEDIUM", "HIGH"],
            help="Affects which detection layers are active"
        )

    st.markdown("---")

    if st.button("🔍 Analyze Prompt", use_container_width=True, type="primary"):
        if not user_prompt.strip():
            st.error("Please enter a prompt to analyze")
        else:
            with st.spinner("Analyzing prompt..."):
                # Run detection
                result = detect_prompt_injection(user_prompt, risk_tier=risk_tier)

                # Log event
                logger = AuditLogger()
                event_id = logger.log_injection_detection(
                    "HR Assistant",
                    user_prompt,
                    result
                )
                st.session_state.audit_log.append({
                    "event_id": event_id,
                    "timestamp": __import__('datetime').datetime.now().isoformat(),
                    "event_type": "injection_detection",
                    "agent_name": "HR Assistant",
                    "action": "prompt_check",
                    "result": result["verdict"],
                    "risk_score": result.get("confidence", 0),
                    "details": {
                        "threat_level": result.get("threat_level"),
                        "confidence": result.get("confidence")
                    }
                })

                if result["verdict"] == "BLOCKED":
                    st.session_state.violations.append(st.session_state.audit_log[-1])

                # Display results
                st.subheader("📊 Detection Results")

                col1, col2, col3 = st.columns(3)

                with col1:
                    verdict_color = "🟢" if result["verdict"] == "ALLOWED" else "🔴" if result["verdict"] == "BLOCKED" else "🟡"
                    st.metric("Verdict", f"{verdict_color} {result['verdict']}")

                with col2:
                    st.metric("Threat Level", result.get("threat_level", "NONE"))

                with col3:
                    confidence = result.get("confidence", 0)
                    st.metric("Confidence", f"{confidence:.1%}")

                st.markdown("---")

                # Detailed analysis
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Detection Layers")

                    heuristic_score = result.get("heuristic_score", 0)
                    semantic_score = result.get("semantic_score", 0)

                    st.write("**Heuristic Check** (Pattern matching)")
                    st.progress(heuristic_score, text=f"{heuristic_score:.1%}")

                    if risk_tier in ["MEDIUM", "HIGH"]:
                        st.write("**Semantic Check** (Similarity)")
                        st.progress(semantic_score, text=f"{semantic_score:.1%}")

                    if risk_tier == "HIGH":
                        final_score = result.get("confidence", 0)
                        st.write("**LLM Judge** (Reasoning)")
                        st.progress(final_score, text=f"{final_score:.1%}")

                with col2:
                    st.subheader("Analysis Details")

                    st.info(f"**Reasoning**: {result.get('reasoning', 'No reasoning provided')}")

                    if result["requires_escalation"]:
                        st.warning("⚠️ **Escalation Required**: Manual review recommended")

                # Show similar attack scenarios
                st.markdown("---")
                st.subheader("📚 Attack Pattern Catalog")

                attack_types = set(s["category"] for s in attack_scenarios)
                for category in sorted(attack_types):
                    with st.expander(f"🎯 {category.upper()} Attacks"):
                        category_attacks = [s for s in attack_scenarios if s["category"] == category]
                        for attack in category_attacks:
                            st.markdown(f"""
                            **{attack['id']}**: {attack['description']}
                            - Difficulty: {attack.get('difficulty', 'unknown')}
                            - Expected outcome: {attack.get('expected_outcome', 'unknown')}
                            """)
