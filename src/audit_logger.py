from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import uuid

class AuditLogger:
    """In-memory audit logger for governance events"""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.violations: List[Dict[str, Any]] = []
        self.approvals: List[Dict[str, Any]] = []

    def log_event(
        self,
        event_type: str,
        agent_name: str,
        action: str,
        result: str,
        details: Dict[str, Any] = None,
        risk_score: float = 0.0,
        policy_version: str = "1.0"
    ) -> str:
        """Log a governance event"""

        event_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()

        event = {
            "event_id": event_id,
            "timestamp": timestamp,
            "event_type": event_type,  # "injection_detection", "rag_validation", "onboarding", "audit"
            "agent_name": agent_name,
            "action": action,
            "result": result,  # "ALLOWED", "BLOCKED", "ESCALATED", "APPROVED", "REJECTED"
            "risk_score": risk_score,
            "policy_version": policy_version,
            "details": details or {}
        }

        self.events.append(event)

        # Track violations
        if result in ["BLOCKED", "ESCALATED", "REJECTED"]:
            self.violations.append(event)

        # Track approvals
        if result in ["APPROVED", "AUTO_APPROVED"]:
            self.approvals.append(event)

        return event_id

    def log_injection_detection(
        self,
        agent_name: str,
        prompt: str,
        detection_result: Dict[str, Any]
    ) -> str:
        """Log prompt injection detection"""

        return self.log_event(
            event_type="injection_detection",
            agent_name=agent_name,
            action="prompt_check",
            result=detection_result["verdict"],
            details={
                "prompt": prompt[:200],  # First 200 chars
                "threat_level": detection_result.get("threat_level", "NONE"),
                "confidence": detection_result.get("confidence", 0.0),
                "heuristic_score": detection_result.get("heuristic_score", 0.0),
                "semantic_score": detection_result.get("semantic_score", 0.0)
            },
            risk_score=detection_result.get("confidence", 0.0)
        )

    def log_rag_validation(
        self,
        agent_name: str,
        query: str,
        validation_result: Dict[str, Any]
    ) -> str:
        """Log RAG response validation"""

        is_safe = validation_result.get("is_safe", False)

        return self.log_event(
            event_type="rag_validation",
            agent_name=agent_name,
            action="response_validation",
            result="ALLOWED" if is_safe else "REDACTED",
            details={
                "query": query[:100],
                "sources_retrieved": len(validation_result.get("sources", [])),
                "pii_redacted": validation_result.get("validation", {}).get("pii_redacted", 0),
                "unsourced_pii": len(validation_result.get("validation", {}).get("unsourced_pii", []))
            },
            risk_score=1.0 - validation_result.get("validation", {}).get("validation_score", 0.5)
        )

    def log_onboarding(
        self,
        agent_name: str,
        risk_assessment: Dict[str, Any]
    ) -> str:
        """Log agent onboarding"""

        auto_approve = risk_assessment.get("auto_approve", False)

        return self.log_event(
            event_type="onboarding",
            agent_name=agent_name,
            action="register_agent",
            result="AUTO_APPROVED" if auto_approve else "ESCALATED",
            details={
                "risk_tier": risk_assessment.get("risk_tier", "UNKNOWN"),
                "risk_score": risk_assessment.get("risk_score", 0.0),
                "escalation_reason": risk_assessment.get("escalation_reason", None),
                "checklist_items": len(risk_assessment.get("checklist", {}))
            },
            risk_score=risk_assessment.get("risk_score", 0.0)
        )

    def log_audit(
        self,
        agent_name: str,
        audit_type: str,
        findings: List[Dict[str, Any]]
    ) -> str:
        """Log scheduled audit"""

        has_issues = any(f.get("severity", "LOW") in ["HIGH", "CRITICAL"] for f in findings)

        return self.log_event(
            event_type="audit",
            agent_name=agent_name,
            action=audit_type,  # "red_team", "entitlement_sweep", "version_drift"
            result="FOUND_ISSUES" if has_issues else "PASSED",
            details={
                "findings_count": len(findings),
                "critical_count": len([f for f in findings if f.get("severity") == "CRITICAL"]),
                "high_count": len([f for f in findings if f.get("severity") == "HIGH"]),
                "findings": findings[:5]  # Top 5
            },
            risk_score=0.5 if has_issues else 0.0
        )

    def get_agent_events(self, agent_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all events for an agent"""
        agent_events = [e for e in self.events if e["agent_name"] == agent_name]
        return agent_events[-limit:]

    def get_violations(self, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all violations, optionally filtered by agent"""
        if agent_name:
            return [v for v in self.violations if v["agent_name"] == agent_name]
        return self.violations

    def get_stats(self) -> Dict[str, Any]:
        """Get audit log statistics"""

        total_events = len(self.events)
        total_violations = len(self.violations)

        # Count by event type
        event_types = {}
        for event in self.events:
            et = event["event_type"]
            event_types[et] = event_types.get(et, 0) + 1

        # Count by result
        results = {}
        for event in self.events:
            r = event["result"]
            results[r] = results.get(r, 0) + 1

        # Agents involved
        agents = set(e["agent_name"] for e in self.events)

        # Average risk score
        scores = [e["risk_score"] for e in self.events]
        avg_risk = sum(scores) / len(scores) if scores else 0

        return {
            "total_events": total_events,
            "total_violations": total_violations,
            "violation_rate": round(total_violations / total_events, 3) if total_events > 0 else 0,
            "event_types": event_types,
            "results": results,
            "unique_agents": len(agents),
            "agents": list(agents),
            "avg_risk_score": round(avg_risk, 3),
            "most_recent_event": self.events[-1]["timestamp"] if self.events else None
        }

    def get_report_data(self) -> Dict[str, Any]:
        """Get all data for report generation"""
        return {
            "events": self.events,
            "violations": self.violations,
            "approvals": self.approvals,
            "stats": self.get_stats(),
            "timestamp": datetime.now().isoformat()
        }


class PolicyVersionTracker:
    """Track policy versions for compliance"""

    def __init__(self):
        self.policies = {
            "1.0": {
                "description": "Initial governance policy",
                "created": "2024-01-01",
                "rules": ["injection_detection", "rag_validation", "onboarding_check"]
            }
        }
        self.current_version = "1.0"

    def get_policy(self, version: str = None) -> Dict[str, Any]:
        """Get policy details"""
        v = version or self.current_version
        return self.policies.get(v, {})

    def record_decision(
        self,
        decision: str,
        policy_version: str,
        evidence: List[str]
    ) -> Dict[str, Any]:
        """Record a governance decision with policy reference"""

        return {
            "decision": decision,
            "policy_version": policy_version,
            "evidence": evidence,
            "timestamp": datetime.now().isoformat(),
            "policy_details": self.get_policy(policy_version)
        }
