import streamlit as st
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from rag_retriever import RAGRetriever, generate_rag_response
from audit_logger import AuditLogger

def show():
    st.title("📚 RAG Retrieval & Response Validation")

    st.markdown("""
    This page demonstrates:
    1. **Knowledge Base Retrieval** - Finding relevant documents via embeddings
    2. **Response Generation** - Creating answers from retrieved sources
    3. **Compliance Validation** - Detecting PII leakage and ensuring source accuracy
    4. **Confidence Scoring** - Assessing response reliability
    """)

    # Initialize retriever
    if st.session_state.get("retriever") is None:
        with st.spinner("Loading knowledge base..."):
            st.session_state.retriever = RAGRetriever("data/knowledge_base")

    st.markdown("---")

    # Query input
    query = st.text_input(
        "Ask a question about HR policies:",
        placeholder="e.g., 'What is the PTO policy?' or 'How much is the salary for engineers?'"
    )

    col1, col2 = st.columns(2)

    with col1:
        top_k = st.slider("Number of sources to retrieve", 1, 5, 3)

    with col2:
        if st.button("🔍 Retrieve & Generate Response", use_container_width=True, type="primary"):
            st.session_state.run_query = True

    st.markdown("---")

    if query and st.session_state.get("run_query", False):
        col1, col2 = st.columns([2, 1], gap="large")

        with col1:
            st.subheader("📖 Retrieved Sources")

            # Retrieve documents
            with st.spinner("Retrieving sources..."):
                retriever = st.session_state.retriever
                sources = retriever.retrieve(query, top_k=top_k)

            if not sources:
                st.warning("No relevant sources found")
            else:
                for i, source in enumerate(sources, 1):
                    with st.expander(f"📄 Source {i}: {source['document']} (confidence: {source['confidence']:.2%})"):
                        st.write(source["content"])

            st.markdown("---")

            st.subheader("🤖 Generated Response")

            # Generate response
            with st.spinner("Generating response..."):
                rag_result = generate_rag_response(query, retriever)

            response = rag_result["response"]
            validation = rag_result.get("validation", {})
            is_safe = rag_result.get("is_safe", False)

            # Show response
            st.write(response)

            # Log the event
            event_id = None
            if st.session_state.retriever:
                logger = AuditLogger()
                event_id = logger.log_rag_validation(
                    "HR Assistant",
                    query,
                    rag_result
                )
                st.session_state.audit_log.append({
                    "event_id": event_id,
                    "timestamp": __import__('datetime').datetime.now().isoformat(),
                    "event_type": "rag_validation",
                    "agent_name": "HR Assistant",
                    "action": "response_validation",
                    "result": "ALLOWED" if is_safe else "REDACTED",
                    "risk_score": 1.0 - validation.get("validation_score", 0.5),
                    "details": {
                        "query": query,
                        "sources_retrieved": len(rag_result.get("sources", [])),
                        "pii_redacted": validation.get("pii_redacted", 0)
                    }
                })

        with col2:
            st.subheader("🔍 Validation Results")

            if not validation:
                st.warning("No validation data")
            else:
                pii_found = validation.get("pii_found", [])
                unsourced_pii = validation.get("unsourced_pii", [])
                redacted_count = validation.get("pii_redacted", 0)

                # Status
                if is_safe:
                    st.success("✅ Response is safe")
                else:
                    st.warning("⚠️ Response required redaction")

                st.metric("PII Redacted", redacted_count)
                st.metric("Unsourced PII", len(unsourced_pii))

                # Validation score
                val_score = validation.get("validation_score", 0)
                st.write(f"**Validation Score**: {val_score:.1%}")
                st.progress(val_score)

                # Details
                if pii_found:
                    st.subheader("Detected PII")
                    for pii in pii_found[:5]:
                        st.write(f"- **{pii['type']}**: {pii['value']}")

                if unsourced_pii:
                    st.subheader("⚠️ Unsourced PII")
                    st.error("PII found in response but not in source documents (potential hallucination)")
                    for pii in unsourced_pii[:3]:
                        st.write(f"- **{pii['type']}**: {pii['value']}")

        st.markdown("---")

        # Show redacted response
        with st.expander("👁️ Show Redacted Response"):
            redacted = validation.get("redacted_response", response)
            st.code(redacted, language="text")

    else:
        st.info("👆 Enter a query and click 'Retrieve & Generate Response' to start")

    st.markdown("---")

    st.subheader("📝 Example Queries")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("What is the PTO policy?"):
            st.session_state.run_query = True

    with col2:
        if st.button("What are the benefits?"):
            st.session_state.run_query = True

    with col3:
        if st.button("Show meeting notes"):
            st.session_state.run_query = True
