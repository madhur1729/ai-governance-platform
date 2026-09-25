from typing import Dict, List, Any
from datetime import datetime
import json


class HTMLReportGenerator:
    """Generate HTML reports from audit data"""

    def __init__(self):
        self.css = """
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: #f5f5f5;
                color: #333;
                line-height: 1.6;
            }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                border-radius: 8px 8px 0 0;
                margin-bottom: 30px;
            }
            h1 { font-size: 28px; margin-bottom: 10px; }
            .subtitle { opacity: 0.9; font-size: 14px; }
            .summary {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .metric-card {
                background: white;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .metric-value {
                font-size: 32px;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 5px;
            }
            .metric-label {
                font-size: 12px;
                color: #999;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            section {
                background: white;
                padding: 30px;
                margin-bottom: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h2 {
                font-size: 20px;
                margin-bottom: 20px;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }
            th {
                background: #f0f0f0;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                border-bottom: 2px solid #ddd;
            }
            td {
                padding: 12px;
                border-bottom: 1px solid #eee;
            }
            tr:hover { background: #f9f9f9; }
            .badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
            }
            .badge-success { background: #d4edda; color: #155724; }
            .badge-warning { background: #fff3cd; color: #856404; }
            .badge-danger { background: #f8d7da; color: #721c24; }
            .badge-info { background: #d1ecf1; color: #0c5460; }
            .violation-item {
                padding: 15px;
                margin-bottom: 10px;
                border-left: 4px solid #f56565;
                background: #fff5f5;
                border-radius: 4px;
            }
            .violation-item.high { border-left-color: #e53e3e; }
            .violation-item.medium { border-left-color: #f6ad55; background: #fffaf0; }
            .violation-item.low { border-left-color: #fbd38d; background: #fffff0; }
            .timestamp { color: #999; font-size: 12px; }
            .tier-LOW { color: #48bb78; }
            .tier-MEDIUM { color: #ed8936; }
            .tier-HIGH { color: #f56565; }
            footer {
                text-align: center;
                padding: 20px;
                color: #999;
                font-size: 12px;
            }
        </style>
        """

    def generate_report(self, audit_data: Dict[str, Any], report_title: str = "AI Governance Audit Report") -> str:
        """Generate complete HTML report"""

        stats = audit_data.get("stats", {})
        events = audit_data.get("events", [])
        violations = audit_data.get("violations", [])
        timestamp = audit_data.get("timestamp", datetime.now().isoformat())

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{report_title}</title>
            {self.css}
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>🛡️ {report_title}</h1>
                    <p class="subtitle">Generated: {timestamp}</p>
                </header>

                {self._generate_summary_section(stats)}
                {self._generate_violations_section(violations)}
                {self._generate_events_section(events)}
                {self._generate_recommendations_section(stats, violations)}

                <footer>
                    <p>This report contains confidential governance and compliance information.</p>
                    <p>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </footer>
            </div>
        </body>
        </html>
        """

        return html

    def _generate_summary_section(self, stats: Dict[str, Any]) -> str:
        """Generate summary metrics section"""

        html = '<div class="summary">'

        metrics = [
            ("Total Events", stats.get("total_events", 0), "info"),
            ("Violations", stats.get("total_violations", 0), "danger" if stats.get("total_violations", 0) > 0 else "success"),
            ("Violation Rate", f"{stats.get('violation_rate', 0) * 100:.1f}%", "warning"),
            ("Unique Agents", stats.get("unique_agents", 0), "info"),
            ("Avg Risk Score", f"{stats.get('avg_risk_score', 0):.2f}/100", "info"),
        ]

        for label, value, badge_class in metrics:
            html += f'''
            <div class="metric-card">
                <div class="metric-value">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
            '''

        html += '</div>'
        return html

    def _generate_violations_section(self, violations: List[Dict[str, Any]]) -> str:
        """Generate violations detail section"""

        if not violations:
            return '<section><h2>✅ No Violations Found</h2><p>All monitored agents are compliant.</p></section>'

        html = '<section><h2>⚠️ Violations & Issues</h2>'

        # Group by severity
        critical = [v for v in violations if v.get("risk_score", 0) > 0.8]
        high = [v for v in violations if 0.5 <= v.get("risk_score", 0) <= 0.8]
        medium = [v for v in violations if v.get("risk_score", 0) < 0.5]

        for severity, items, class_name in [
            ("CRITICAL", critical, "high"),
            ("HIGH", high, "high"),
            ("MEDIUM", medium, "medium")
        ]:
            if items:
                html += f'<h3>{severity} ({len(items)})</h3>'
                for violation in items[:5]:  # Show top 5
                    html += f'''
                    <div class="violation-item {class_name}">
                        <strong>{violation.get("event_type", "Unknown")}</strong> - {violation.get("agent_name", "Unknown")}
                        <br/>
                        <span class="timestamp">{violation.get("timestamp", "")}</span>
                        <br/>
                        Result: <span class="badge badge-danger">{violation.get("result", "")}</span>
                        <br/>
                        Details: {violation.get("details", {})}
                    </div>
                    '''

        html += '</section>'
        return html

    def _generate_events_section(self, events: List[Dict[str, Any]]) -> str:
        """Generate events timeline section"""

        html = '<section><h2>📊 Recent Events</h2>'

        if not events:
            html += '<p>No events recorded.</p>'
            return html + '</section>'

        # Group by agent
        agents_events = {}
        for event in events[-20:]:  # Last 20
            agent = event.get("agent_name", "Unknown")
            if agent not in agents_events:
                agents_events[agent] = []
            agents_events[agent].append(event)

        html += '<table><tr><th>Time</th><th>Agent</th><th>Type</th><th>Action</th><th>Result</th><th>Risk</th></tr>'

        for event in events[-20:]:  # Last 20
            result_badge = self._get_result_badge(event.get("result", ""))
            risk_score = event.get("risk_score", 0)
            risk_color = "danger" if risk_score > 0.7 else "warning" if risk_score > 0.4 else "success"

            html += f'''
            <tr>
                <td><span class="timestamp">{event.get("timestamp", "")[-8:]}</span></td>
                <td>{event.get("agent_name", "")}</td>
                <td>{event.get("event_type", "")}</td>
                <td>{event.get("action", "")}</td>
                <td>{result_badge}</td>
                <td><strong class="tier-{('HIGH' if risk_score > 0.7 else 'MEDIUM' if risk_score > 0.4 else 'LOW')}">{risk_score:.2f}</strong></td>
            </tr>
            '''

        html += '</table></section>'
        return html

    def _generate_recommendations_section(self, stats: Dict[str, Any], violations: List[Dict[str, Any]]) -> str:
        """Generate recommendations section"""

        html = '<section><h2>💡 Recommendations</h2><ul>'

        # Smart recommendations based on data
        if stats.get("total_violations", 0) > 5:
            html += '<li><strong>High violation rate:</strong> Review agent system prompts and access controls for over-permissioned agents.</li>'

        if stats.get("unique_agents", 0) > 10:
            html += '<li><strong>Large agent portfolio:</strong> Implement automated risk scoring and tier-based approval workflows.</li>'

        high_risk_agents = set(v.get("agent_name") for v in violations if v.get("risk_score", 0) > 0.7)
        if high_risk_agents:
            html += f'<li><strong>High-risk agents detected:</strong> {", ".join(list(high_risk_agents)[:3])} require escalated review.</li>'

        html += '''
            <li>Schedule weekly governance reviews to catch drift early.</li>
            <li>Implement continuous monitoring for injection attempts and data leakage.</li>
            <li>Document all exceptions and waivers with expiration dates.</li>
        </ul></section>
        '''

        return html

    def _get_result_badge(self, result: str) -> str:
        """Get badge HTML for result"""
        badge_map = {
            "ALLOWED": ("badge-success", "✅ Allowed"),
            "BLOCKED": ("badge-danger", "🚫 Blocked"),
            "ESCALATED": ("badge-warning", "⚠️ Escalated"),
            "REDACTED": ("badge-warning", "🔍 Redacted"),
            "AUTO_APPROVED": ("badge-success", "✅ Auto-Approved"),
            "APPROVED": ("badge-success", "✅ Approved"),
            "REJECTED": ("badge-danger", "❌ Rejected"),
            "FOUND_ISSUES": ("badge-danger", "⚠️ Issues Found"),
            "PASSED": ("badge-success", "✅ Passed"),
        }

        badge_class, label = badge_map.get(result, ("badge-info", result))
        return f'<span class="badge {badge_class}">{label}</span>'


class ReportExporter:
    """Export reports to files"""

    @staticmethod
    def save_html(html_content: str, filename: str = "governance_report.html") -> str:
        """Save HTML report to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return filename

    @staticmethod
    def save_json(data: Dict[str, Any], filename: str = "governance_audit.json") -> str:
        """Save audit data as JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        return filename
