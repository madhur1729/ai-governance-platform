import yaml
from typing import Dict, List, Any, Tuple
from pathlib import Path
import json

class OnboardingScorer:
    def __init__(self, config_path: str = "config/checklist_rules.yaml"):
        self.config = self._load_config(config_path)
        self.checklist_rules = self.config.get("checklist_rules", [])
        self.approved_tools = self.config.get("approved_tools", [])
        self.tool_risk_levels = self.config.get("tool_risk_levels", {})
        self.data_classification = self.config.get("data_classification", {})

    def _load_config(self, config_path: str) -> Dict:
        """Load YAML config file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Config file {config_path} not found, using defaults")
            return {
                "checklist_rules": [],
                "approved_tools": [],
                "tool_risk_levels": {},
                "data_classification": {}
            }

    def validate_tool_scope(self, tools: List[str]) -> Tuple[bool, str, List[str]]:
        """Validate tools against approved list"""
        unapproved = [t for t in tools if t not in self.approved_tools]

        if unapproved:
            return False, f"Unapproved tools: {', '.join(unapproved)}", unapproved
        return True, "All tools approved", []

    def classify_data_access(self, data_types: List[str]) -> Dict[str, Any]:
        """Classify data being accessed"""
        classification = {
            "data_types": data_types,
            "tiers": [],
            "sensitive": False,
            "pii_access": False,
            "highest_tier": "LOW"
        }

        tier_hierarchy = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        max_tier = "LOW"

        for data_type in data_types:
            data_info = self.data_classification.get(data_type, {})
            tier = data_info.get("tier", "LOW")
            classification["tiers"].append({"type": data_type, "tier": tier})

            if tier_hierarchy.get(tier, 0) > tier_hierarchy.get(max_tier, 0):
                max_tier = tier

            if tier == "HIGH":
                classification["pii_access"] = True
                classification["sensitive"] = True

        classification["highest_tier"] = max_tier
        return classification

    def check_privilege_escalation(self, tools: List[str], data_types: List[str]) -> Tuple[bool, str, str]:
        """Check if escalation is required"""

        # Check for external/write tools
        has_external = any(t in self.tool_risk_levels.get("external_tools", []) for t in tools)
        has_write = any(t in self.tool_risk_levels.get("write_tools", []) for t in tools)

        # Check for high-value data
        data_class = self.classify_data_access(data_types)
        has_pii = data_class["pii_access"]

        requires_escalation = has_external or has_write or has_pii

        if has_external and has_pii:
            return True, "Escalation required: external tools + PII access", "CRITICAL"
        elif has_pii:
            return True, "Escalation required: PII/PHI access", "HIGH"
        elif has_external:
            return True, "Escalation required: external effects (email)", "MEDIUM"
        elif has_write:
            return True, "Escalation required: write access", "MEDIUM"
        else:
            return False, "No escalation needed", "LOW"

    def detect_over_scope(self, tools: List[str], use_case: str) -> Tuple[List[str], str]:
        """Flag over-scoped tools"""

        over_scoped = []

        # Simple heuristic: if agent uses write/external tools but is just for query, it's over-scoped
        if "query" in use_case.lower() or "retrieve" in use_case.lower():
            write_tools = self.tool_risk_levels.get("write_tools", [])
            external_tools = self.tool_risk_levels.get("external_tools", [])
            over_scoped = [t for t in tools if t in write_tools or t in external_tools]

        if over_scoped:
            reason = f"Read-only agent should not have: {', '.join(over_scoped)}"
            return over_scoped, reason

        return [], "No over-scoping detected"

    def compute_risk_score(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        """Compute overall risk score for an agent"""

        tools = agent.get("tools", [])
        data_types = agent.get("data_accessed", [])
        use_case = agent.get("use_case", "")

        scores = {}
        total_weight = 0
        weighted_sum = 0

        # Run each checklist rule
        for rule in self.checklist_rules:
            rule_id = rule["id"]
            rule_name = rule["name"]
            weight = rule["weight"]

            if rule_id == "tool_scope_check":
                passed, msg, unapproved = self.validate_tool_scope(tools)
                score = 100 if passed else 0
                status = "✅ PASS" if passed else "❌ FAIL"

            elif rule_id == "data_classification":
                data_class = self.classify_data_access(data_types)
                tier = data_class["highest_tier"]
                tier_values = {"LOW": 100, "MEDIUM": 50, "HIGH": 0}
                score = tier_values.get(tier, 50)
                msg = f"Highest data tier: {tier}"
                status = "⚠️ " + tier

            elif rule_id == "privilege_check":
                requires, msg, severity = self.check_privilege_escalation(tools, data_types)
                score = 0 if requires else 100
                status = "⚠️ ESCALATION NEEDED" if requires else "✅ PASS"

            elif rule_id == "over_scope_detection":
                over_scoped, msg = self.detect_over_scope(tools, use_case)
                score = 100 if not over_scoped else 20
                status = "⚠️ OVER-SCOPED" if over_scoped else "✅ PASS"

            elif rule_id == "vendor_contract_check":
                # Mocked: always pass in demo
                score = 100
                msg = "Vendor contract verified (mocked)"
                status = "✅ PASS"

            else:
                score = 50
                status = "❓ UNKNOWN"
                msg = "Rule not implemented"

            scores[rule_id] = {
                "name": rule_name,
                "score": score,
                "weight": weight,
                "status": status,
                "message": msg
            }

            weighted_sum += score * weight
            total_weight += weight

        # Compute final risk score (0-100, higher = more risky)
        risk_score = 100 - (weighted_sum / total_weight) if total_weight > 0 else 50

        # Determine risk tier
        if risk_score < 30:
            risk_tier = "LOW"
            auto_approve = True
        elif risk_score < 70:
            risk_tier = "MEDIUM"
            auto_approve = False
        else:
            risk_tier = "HIGH"
            auto_approve = False

        return {
            "agent_name": agent.get("name", "Unknown"),
            "risk_score": round(risk_score, 2),
            "risk_tier": risk_tier,
            "auto_approve": auto_approve,
            "checklist": scores,
            "total_weight": total_weight,
            "requires_human_review": not auto_approve,
            "escalation_reason": _get_escalation_reason(scores) if not auto_approve else None
        }


def _get_escalation_reason(scores: Dict) -> str:
    """Generate escalation reason from failed checks"""
    reasons = []

    for check_id, check in scores.items():
        if "FAIL" in check["status"] or "ESCALATION" in check["status"] or "OVER-SCOPED" in check["status"]:
            reasons.append(f"{check['name']}: {check['message']}")

    return " | ".join(reasons) if reasons else "Manual review requested"


class VersionManager:
    """Track agent versions and detect changes"""

    def __init__(self):
        self.versions = {}

    def register_version(self, agent_name: str, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new agent version"""

        import hashlib
        from datetime import datetime

        # Create config hash
        config_str = json.dumps(agent_config, sort_keys=True)
        config_hash = hashlib.md5(config_str.encode()).hexdigest()

        version = {
            "timestamp": datetime.now().isoformat(),
            "config": agent_config,
            "config_hash": config_hash,
            "version_id": f"v{len(self.versions.get(agent_name, [])) + 1}"
        }

        if agent_name not in self.versions:
            self.versions[agent_name] = []

        self.versions[agent_name].append(version)
        return version

    def detect_changes(self, agent_name: str, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Detect if agent config has changed"""

        if agent_name not in self.versions or not self.versions[agent_name]:
            return {"changed": True, "reason": "New agent", "changes": []}

        import hashlib
        old_version = self.versions[agent_name][-1]

        old_hash = old_version["config_hash"]
        new_str = json.dumps(new_config, sort_keys=True)
        new_hash = hashlib.md5(new_str.encode()).hexdigest()

        if old_hash == new_hash:
            return {"changed": False, "reason": "No changes detected", "changes": []}

        # Detect specific changes
        changes = []
        old_config = old_version["config"]

        if old_config.get("tools") != new_config.get("tools"):
            changes.append("Tool scope changed")

        if old_config.get("system_prompt") != new_config.get("system_prompt"):
            changes.append("System prompt modified")

        if old_config.get("data_accessed") != new_config.get("data_accessed"):
            changes.append("Data access scope changed")

        return {
            "changed": True,
            "reason": "Configuration modified",
            "changes": changes,
            "requires_review": True
        }
