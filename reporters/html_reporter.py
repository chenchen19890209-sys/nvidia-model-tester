"""HTML report generator — produces a comprehensive, self-contained report."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from config import settings
from models.scanner import ModelInfo
from tests.base import TestResult


@dataclass
class ModelReportData:
    """Aggregated test results for one model."""

    model: ModelInfo
    results: dict[str, TestResult] = field(default_factory=dict)

    @property
    def overall_score(self) -> float:
        scores = [r.score for r in self.results.values()]
        return sum(scores) / len(scores) if scores else 0.0

    @property
    def passed_tests(self) -> list[str]:
        return [n for n, r in self.results.items() if r.passed]

    @property
    def failed_tests(self) -> list[str]:
        return [n for n, r in self.results.items() if not r.passed]

    @property
    def all_errors(self) -> list[str]:
        errors: list[str] = []
        for r in self.results.values():
            errors.extend(r.errors)
        return errors


# ── CSS constant (not inside f-string) ─────────────────────────

_CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #0b0f1a; color: #e2e8f0; padding: 24px;
}
.container { max-width: 1400px; margin: 0 auto; }

.header { padding: 32px 0 24px; border-bottom: 1px solid #1e2a3a; margin-bottom: 32px; }
.header h1 { font-size: 28px; font-weight: 700; color: #fff; }
.header .subtitle { color: #8892a4; margin-top: 8px; font-size: 14px; }
.header .badge {
  display: inline-block; background: #76b900; color: #000;
  padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 600;
}

.card { background: #131926; border: 1px solid #1e2a3a; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
.card h2 { font-size: 18px; font-weight: 600; margin-bottom: 16px; color: #fff; }
.card h3 { font-size: 14px; font-weight: 600; margin-bottom: 8px; color: #8892a4; }

.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 24px; }
.stat {
  background: #131926; border: 1px solid #1e2a3a; border-radius: 8px;
  padding: 16px; text-align: center;
}
.stat .value { font-size: 28px; font-weight: 700; color: #fff; }
.stat .label { font-size: 12px; color: #8892a4; margin-top: 4px; }

table { width: 100%; border-collapse: collapse; font-size: 13px; }
th {
  text-align: left; padding: 10px 12px; border-bottom: 2px solid #1e2a3a;
  color: #8892a4; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
}
td { padding: 10px 12px; border-bottom: 1px solid #1e2a3a; }
tr:hover td { background: #1a2332; }

.rank-num { font-weight: 700; color: #8892a4; width: 32px; }
.model-name { font-weight: 500; color: #fff; }
.model-cat { font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #1e2a3a; color: #8892a4; }

.score-bar { height: 6px; background: #1e2a3a; border-radius: 3px; overflow: hidden; min-width: 120px; }
.score-fill { height: 100%; border-radius: 3px; transition: width 0.6s; }
.score-fill.green { background: #76b900; }
.score-fill.orange { background: #f59e0b; }
.score-fill.red { background: #ef4444; }

.tag { display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 4px; margin: 2px; font-weight: 500; }
.tag.green { background: rgba(118, 185, 0, 0.15); color: #76b900; }
.tag.red { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.tag.orange { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.tag.blue { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }

.matrix-cell {
  padding: 4px 8px; border-radius: 4px; text-align: center;
  font-size: 12px; font-weight: 500;
}
.matrix-cell.s4 { background: rgba(118, 185, 0, 0.25); color: #76b900; }
.matrix-cell.s3 { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.matrix-cell.s2 { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.matrix-cell.s1 { background: rgba(239, 68, 68, 0.08); color: #8892a4; }
.matrix-cell.s0 { background: transparent; color: #8892a4; }

.model-card { background: #131926; border: 1px solid #1e2a3a; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
.model-card h4 { font-size: 14px; font-weight: 600; color: #fff; cursor: pointer; }
.model-card h4:hover { opacity: 0.8; }
.model-card .sub-detail { font-size: 12px; color: #8892a4; margin: 4px 0 8px; }

.detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; }
.detail-item { font-size: 12px; }
.detail-item .label { color: #8892a4; }
.detail-item .value { color: #fff; font-weight: 500; }

.errors-box {
  background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 6px; padding: 10px; margin-top: 8px; font-size: 12px; color: #ef4444;
}

.footer { text-align: center; padding: 40px 0; color: #8892a4; font-size: 12px; }
.chart-container { width: 100%; height: 400px; margin: 16px 0; }

@media (max-width: 768px) {
  .stats { grid-template-columns: repeat(2, 1fr); }
  table { font-size: 12px; }
}
"""

_JS_CHART = """
const CHART_DATA = %s;

function drawBars() {
  var canvas = document.getElementById('overallChart');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  var dpr = window.devicePixelRatio || 1;
  var rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  var w = rect.width, h = rect.height;
  var pad = {left: 80, right: 30, top: 30, bottom: 80};
  var chartW = w - pad.left - pad.right;
  var chartH = h - pad.top - pad.bottom;

  var data = CHART_DATA.overall;
  if (!data || data.length === 0) return;

  var maxScore = 1.0;
  
  // 动态计算柱子宽度，避免过密
  var gap = 12; // 柱子之间的间距
  var barW = Math.max(8, Math.min(30, (chartW - gap * (data.length + 1)) / data.length));
  var count = data.length;
  
  // 如果太密，只显示前15个
  if (barW < 10 && data.length > 15) {
    data = data.slice(0, 15);
    count = data.length;
    barW = Math.max(10, (chartW - gap * (count + 1)) / count);
  }
  
  var totalW = count * (barW + gap);
  var offset = Math.max(0, (chartW - totalW) / 2);

  ctx.clearRect(0, 0, w, h);

  // 绘制Y轴网格线
  for (var i = 0; i <= 5; i++) {
    var y = pad.top + chartH - (i / 5) * chartH;
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(w - pad.right, y);
    ctx.stroke();
    ctx.fillStyle = '#8892a4';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText((i / 5).toFixed(1), pad.left - 8, y + 3);
  }

  // 绘制柱子
  for (var i = 0; i < data.length; i++) {
    var d = data[i];
    var x = pad.left + offset + i * (barW + gap);
    var barH = (d.score / maxScore) * chartH;
    var y = pad.top + chartH - barH;

    var gradient = ctx.createLinearGradient(0, y, 0, pad.top + chartH);
    gradient.addColorStop(0, '#76b900');
    gradient.addColorStop(1, '#5a8f00');
    ctx.fillStyle = gradient;

    var r = 3;
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + barW - r, y);
    ctx.quadraticCurveTo(x + barW, y, x + barW, y + r);
    ctx.lineTo(x + barW, pad.top + chartH);
    ctx.lineTo(x, pad.top + chartH);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.fill();

    // 绘制分数（柱子上方）
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(d.score.toFixed(2), x + barW / 2, y - 6);
    
    // 绘制模型名称（旋转45度避免重叠）
    ctx.save();
    ctx.translate(x + barW / 2, pad.top + chartH + 16);
    ctx.rotate(-Math.PI / 4);
    ctx.fillStyle = '#8892a4';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'right';
    var label = d.name;
    if (label.length > 20) {
      label = label.slice(0, 20) + '..';
    }
    ctx.fillText(label, 0, 0);
    ctx.restore();
  }
}

window.addEventListener('load', drawBars);
window.addEventListener('resize', drawBars);
"""


class HTMLReporter:
    """Generate a complete, styled HTML report with rankings and charts."""

    def __init__(self, output_dir: str = "") -> None:
        self.output_dir = output_dir or settings.OUTPUT_DIR

    def generate(
        self,
        models_data: list[ModelReportData],
        run_timestamp: Optional[str] = None,
    ) -> str:
        """Generate the HTML report and return the file path."""
        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = run_timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(
            self.output_dir, f"nvidia_report_{timestamp}.html"
        )

        models_data.sort(key=lambda m: m.overall_score, reverse=True)

        html = self._build_html(models_data, timestamp)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"  \U0001f4c4 Report saved to: {filepath}")
        return filepath

    def _build_html(
        self, models: list[ModelReportData], timestamp: str
    ) -> str:
        chart_json = json.dumps(
            {"overall": self._chart_overall(models)}, ensure_ascii=False
        )
        js_filled = _JS_CHART % chart_json

        sections = "".join([
            self._section_executive_summary(models),
            self._section_rankings(models),
            self._section_dimensions(models),
            self._section_scenario_suitability(models),
            self._section_cost_analysis(models),
            self._section_model_cards(models),
        ])

        return (
            "<!DOCTYPE html>\n<html lang='zh-CN'>\n<head>\n"
            "<meta charset='UTF-8'>\n"
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
            f"<title>{settings.REPORT_TITLE}</title>\n"
            f"<style>{_CSS}</style>\n"
            "</head>\n<body>\n<div class='container'>\n"
            f"<div class='header'>"
            f"<h1>\U0001f3c6 {settings.REPORT_TITLE}</h1>"
            f"<div class='subtitle'>"
            f"Generated: {timestamp} &nbsp;|&nbsp; "
            f"<span class='badge'>{len(models)} Models Tested</span>"
            f" &nbsp;|&nbsp; NVIDIA NIM API"
            f"</div></div>\n"
            f"{sections}\n"
            f"<div class='footer'>"
            f"<p>NVIDIA Model Tester &mdash; Built with NVIDIA NIM API</p>"
            f"<p style='margin-top:4px'>Report generated at {timestamp}</p>"
            f"</div>\n"
            f"</div>\n"
            f"<script>{js_filled}</script>\n"
            "</body>\n</html>"
        )

    # ── Section builders ───────────────────────────────────────

    @staticmethod
    def _section_executive_summary(models: list[ModelReportData]) -> str:
        total = len(models)
        passed_all = sum(
            1
            for m in models
            if m.results and all(r.passed for r in m.results.values())
        )
        avg_score = (
            sum(m.overall_score for m in models) / total if total else 0
        )
        categories = len(set(m.model.category for m in models))
        best = models[0] if models else None

        return (
            "<div class='stats'>"
            f"<div class='stat'><div class='value'>{total}</div>"
            "<div class='label'>Models Tested</div></div>"
            f"<div class='stat'><div class='value'>{categories}</div>"
            "<div class='label'>Categories</div></div>"
            f"<div class='stat'><div class='value'>{passed_all}</div>"
            "<div class='label'>All Tests Passed</div></div>"
            f"<div class='stat'><div class='value'>{avg_score:.2f}</div>"
            "<div class='label'>Average Score</div></div>"
            f"<div class='stat'><div class='value' style='font-size:16px'>"
            f"{best.model.id if best else '&mdash;'}</div>"
            "<div class='label'>Top Model</div></div>"
            "</div>"
        )

    def _section_rankings(self, models: list[ModelReportData]) -> str:
        rows = ""
        for i, m in enumerate(models[:30]):
            score = m.overall_score
            css = "green" if score >= 0.7 else ("orange" if score >= 0.4 else "red")
            fill_w = f"{score * 100:.1f}%"

            result_tags = ""
            for tname, tr in m.results.items():
                cls = "green" if tr.passed else "red"
                result_tags += f"<span class='tag {cls}'>{tname}</span> "

            rows += (
                "<tr>"
                f"<td class='rank-num'>{i + 1}</td>"
                f"<td><span class='model-name'>{m.model.id}</span><br>"
                f"<span class='model-cat'>{m.model.category}</span></td>"
                f"<td>"
                f"<div class='score-bar'><div class='score-fill {css}' "
                f"style='width:{fill_w}'></div></div>"
                f"<div style='font-size:12px;margin-top:2px'>{score:.1%}</div>"
                f"</td>"
                f"<td>{result_tags}</td>"
                "</tr>"
            )

        n = min(30, len(models))
        return (
            "<div class='card'>"
            f"<h2>\U0001f4ca Overall Rankings (Top {n})</h2>"
            "<div class='chart-container'><canvas id='overallChart'>"
            "</canvas></div>"
            "<table><thead><tr>"
            "<th>#</th><th>Model</th><th>Score</th><th>Tests</th>"
            "</tr></thead>"
            f"<tbody>{rows}</tbody></table></div>"
        )

    def _section_dimensions(self, models: list[ModelReportData]) -> str:
        all_dims = ["availability", "performance", "capability", "quality"]
        dim_labels = {
            "availability": "Availability",
            "performance": "Performance",
            "capability": "Capability",
            "quality": "Quality",
        }
        # Only include dimensions that have data
        dims_with_data = {d for m in models for d in m.results}
        dimensions = [d for d in all_dims if d in dims_with_data]

        cols = ""
        for dim in dimensions:
            ranked = [
                (m, m.results.get(dim))
                for m in models
                if dim in m.results
            ]
            ranked.sort(key=lambda x: x[1].score if x[1] else 0, reverse=True)

            top5 = ranked[:5]
            rows = ""
            for j, (m, r) in enumerate(top5):
                if r:
                    pct = f"{r.score:.1%}"
                    cls = "green" if r.passed else "red"
                    rows += (
                        "<tr>"
                        f"<td style='width:24px;color:#8892a4'>{j + 1}</td>"
                        f"<td style='color:#fff;font-size:12px'>"
                        f"{m.model.id.split('/')[-1]}</td>"
                        f"<td><span class='tag {cls}'>{pct}</span></td>"
                        "</tr>"
                    )

            cols += (
                "<div style='background:#131926;border:1px solid #1e2a3a;"
                "border-radius:8px;padding:12px'>"
                f"<h3 style='margin-bottom:8px'>{dim_labels.get(dim, dim)}</h3>"
                f"<table>{rows}</table></div>"
            )

        return (
            "<div class='card'>"
            "<h2>\U0001f3af Per-Dimension Analysis</h2>"
            "<div style='display:grid;grid-template-columns:"
            "repeat(auto-fit,minmax(280px,1fr));gap:16px'>"
            f"{cols}</div></div>"
        )

    def _section_scenario_suitability(
        self, models: list[ModelReportData]
    ) -> str:
        all_scenarios: set[str] = set()
        model_scenarios: dict[str, dict[str, float]] = {}
        for m in models:
            cap = m.results.get("capability")
            if cap and "scenarios" in cap.details:
                sc = cap.details["scenarios"]
                if isinstance(sc, dict):
                    model_scenarios[m.model.id] = sc
                    all_scenarios.update(sc.keys())

        if not all_scenarios:
            return ""

        sorted_scenarios = sorted(all_scenarios)
        from scenarios.prompts import PROMPTS_BY_ID

        # Build table header
        header = "<tr><th style='width:250px'>Model</th><th style='width:80px'>Type</th>"
        for sid in sorted_scenarios:
            prompt = PROMPTS_BY_ID.get(sid)
            label = prompt.label if prompt else sid[:24]
            header += f"<th style='min-width:80px;text-align:center' title='{label}'>{label[:14]}</th>"
        header += "</tr>"

        # Build table body
        body_rows = ""
        for m in models[:20]:
            if m.model.id not in model_scenarios:
                continue
                
            scs = model_scenarios[m.model.id]
            short = m.model.id.split("/")[-1]
            
            row = f"<tr><td style='color:#fff;font-size:12px;font-weight:500;white-space:nowrap'>{short}</td>"
            row += f"<td><span class='model-cat'>{m.model.category}</span></td>"
            
            for sid in sorted_scenarios:
                score = scs.get(sid, 0.0)
                lvl = min(4, int(score * 5))
                display = round(score * 10) / 10  # avoid float imprecision
                row += f"<td style='text-align:center'><div class='matrix-cell s{lvl}' title='{sid}: {display:.2f}'>{display:.1f}</div></td>"
            
            row += "</tr>"
            body_rows += row

        return (
            "<div class='card'>"
            "<h2>\U0001f9e9 Scenario Suitability Matrix</h2>"
            "<p style='font-size:12px;color:#8892a4;margin-bottom:12px'>"
            "Higher scores (0.0&ndash;1.0) indicate better suitability. "
            "Shows top 20 models.</p>"
            "<div style='overflow-x:auto'>"
            "<table><thead>" + header + "</thead>"
            "<tbody>" + body_rows + "</tbody></table></div></div>"
        )

    def _section_cost_analysis(self, models: list[ModelReportData]) -> str:
        rows = ""
        for m in models:
            cap = m.results.get("capability")
            if not cap:
                continue
            det = cap.details
            total_tokens = det.get("total_tokens", 0)
            prompt_tokens = det.get("total_prompt_tokens", 0)
            completion_tokens = det.get("total_completion_tokens", 0)

            input_cost = (
                prompt_tokens / 1000 * settings.COST_PER_1K_INPUT_TOKENS
            )
            output_cost = (
                completion_tokens / 1000 * settings.COST_PER_1K_OUTPUT_TOKENS
            )
            total_cost = input_cost + output_cost

            short = m.model.id.split("/")[-1]
            rows += (
                "<tr>"
                f"<td style='color:#fff'>{short}</td>"
                f"<td>{total_tokens:,}</td>"
                f"<td>{prompt_tokens:,}</td>"
                f"<td>{completion_tokens:,}</td>"
                f"<td>${total_cost:.4f}</td>"
                "</tr>"
            )

        return (
            "<div class='card'>"
            "<h2>\U0001f4b0 Cost &amp; Token Consumption</h2>"
            "<p style='font-size:12px;color:#8892a4;margin-bottom:12px'>"
            "Based on capability test prompts. Costs are rough estimates "
            "using default rates.</p>"
            "<table><thead><tr>"
            "<th>Model</th><th>Total Tokens</th><th>Prompt</th>"
            "<th>Completion</th><th>Est. Cost</th>"
            "</tr></thead>"
            f"<tbody>{rows}</tbody></table></div>"
        )

    def _section_model_cards(self, models: list[ModelReportData]) -> str:
        cards = ""
        for m in models:
            collapsed = " style='display:none'" if len(models) > 10 else ""

            results_html = ""
            for tname, tr in m.results.items():
                cls = "green" if tr.passed else "red"
                detail_rows = self._detail_rows(tr.details)
                results_html += (
                    "<div style='margin-bottom:8px;padding:8px;"
                    "background:rgba(255,255,255,0.02);border-radius:6px'>"
                    "<div style='display:flex;justify-content:space-between'>"
                    f"<strong style='font-size:13px'>{tname}</strong>"
                    f"<span class='tag {cls}'>"
                    f"{'PASS' if tr.passed else 'FAIL'} ({tr.score:.2f})"
                    f"</span></div>{detail_rows}</div>"
                )

            errors_html = ""
            if m.all_errors:
                err_lines = "<br>".join(m.all_errors[:5])
                errors_html = (
                    f"<div class='errors-box'>\u26a0\ufe0f {err_lines}</div>"
                )

            short = m.model.id.split("/")[-1]
            cards += (
                "<div class='model-card'>"
                f"<h4 onclick=\"var n=this.parentElement.querySelector('.card-body');"
                f"n.style.display=n.style.display==='none'?'':'none'\">"
                f"\U0001f4cb {short}</h4>"
                f"<div class='sub-detail'>"
                f"ID: {m.model.id} &nbsp;|&nbsp; Category: {m.model.category}"
                f" &nbsp;|&nbsp; Overall: {m.overall_score:.2f}</div>"
                f"<div class='card-body'{collapsed}>"
                f"{results_html}{errors_html}</div></div>"
            )

        return (
            "<div class='card'>"
            "<h2>\U0001f4cb Detailed Model Cards</h2>"
            f"{cards}</div>"
        )

    @staticmethod
    def _detail_rows(details: dict[str, Any]) -> str:
        items = ""
        for k, v in details.items():
            if isinstance(v, dict):
                # Show nested dict items compactly (scores, etc.)
                nested_parts = []
                for nk, nv in list(v.items())[:5]:
                    if isinstance(nv, float):
                        nested_parts.append(
                            f"<span style='color:#8892a4'>{nk}:</span> "
                            f"<span style='color:#e2e8f0'>{nv:.2f}</span>"
                        )
                    else:
                        nested_parts.append(
                            f"<span style='color:#8892a4'>{nk}:</span> "
                            f"<span style='color:#e2e8f0'>{nv}</span>"
                        )
                if len(v) > 5:
                    nested_parts.append(
                        f"<span style='color:#8892a4'>... +{len(v) - 5} more</span>"
                    )
                nested_html = " &nbsp; ".join(nested_parts)
                items += (
                    f"<div class='detail-item' style='grid-column:1/-1'>"
                    f"<span class='label'>{k}:</span> "
                    f"<span style='font-size:11px'>{nested_html}</span></div>"
                )
                continue
            if isinstance(v, float):
                val = f"{v:.2f}"
            elif isinstance(v, list):
                val = f"{len(v)} items" if len(v) > 5 else str(v)
            else:
                val = str(v)
            items += (
                f"<div class='detail-item'>"
                f"<span class='label'>{k}:</span> "
                f"<span class='value'>{val}</span></div>"
            )
        return f"<div class='detail-grid'>{items}</div>" if items else ""

    @staticmethod
    def _chart_overall(models: list[ModelReportData]) -> list[dict]:
        return [
            {
                "name": m.model.id.split("/")[-1],
                "score": round(m.overall_score, 3),
            }
            for m in models[:20]
        ]
