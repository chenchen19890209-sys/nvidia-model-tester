#!/usr/bin/env python3
"""NVIDIA Model Tester Web UI — 基于浏览器的测试控制台。

启动方式:
    python web_ui.py              # 默认 http://localhost:8080
    python web_ui.py --port 9090  # 自定义端口

功能:
    - 下拉框多选模型（自动从 NVIDIA API 加载）
    - 并发数输入（含速率限制建议 + 校验）
    - 测试维度勾选（可用性、延迟、能力、质量）
    - 实时进度展示
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import threading
import time
import traceback
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

# Fix Windows console encoding to avoid GBK emoji errors in background threads
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )
    except (AttributeError, OSError):
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from utils.api_client import NIMClient

# ── Test runner (reuses existing framework) ──────────────────────

_test_status: dict[str, Any] = {
    "running": False,
    "phase": "",
    "progress": 0,
    "total": 0,
    "model": "",
    "results": [],
    "errors": [],
    "report_path": "",
    "started_at": "",
}


def _run_test_async(
    model_ids: list[str],
    concurrency: int,
    tests: list[str],
) -> None:
    """在后台线程中运行测试，更新全局 _test_status。"""
    global _test_status
    _test_status["running"] = True
    _test_status["phase"] = "discovering"
    _test_status["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _test_status["results"] = []
    _test_status["errors"] = []
    _test_status["report_path"] = ""

    try:
        from models.scanner import discover_models
        from tests.availability import AvailabilityTester
        from tests.performance import PerformanceTester
        from tests.capability import CapabilityTester
        from tests.quality import QualityTester
        from reporters.html_reporter import HTMLReporter, ModelReportData
        from concurrent.futures import ThreadPoolExecutor, as_completed

        client = NIMClient()

        # 发现模型
        _test_status["phase"] = "discovering"
        all_models = discover_models(client)
        models = [m for m in all_models if m.id in model_ids]
        if not models:
            _test_status["errors"].append("未找到匹配的模型")
            _test_status["running"] = False
            return

        result_map: dict[str, ModelReportData] = {
            m.id: ModelReportData(model=m) for m in models
        }

        # 配置并发
        settings.CONCURRENCY = concurrency
        _test_status["total"] = len(models) * len(tests) + len(models)
        _test_status["progress"] = 0

        # 步骤 1: 连通性
        if "availability" in tests:
            _test_status["phase"] = "availability"
            tester = AvailabilityTester(client)
            eligible = [m for m in models if not tester.skip_reason(m)]
            available: list = []
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                fut_map = {pool.submit(tester.test_model, m): m for m in eligible}
                for future in as_completed(fut_map):
                    model = fut_map[future]
                    try:
                        result = future.result()
                        _test_status["progress"] += 1
                        result_map[model.id].results["availability"] = result
                        _test_status["model"] = model.id
                        if result.passed:
                            available.append(model)
                    except Exception as e:
                        _test_status["errors"].append(f"{model.id}: {e}")
        else:
            available = list(models)

        if not available:
            _test_status["running"] = False
            for m in models:
                _test_status["results"].append(result_map[m.id])
            return

        # 步骤 2: 深度测试
        remaining_tests = [t for t in tests if t != "availability"]
        tester_classes: dict[str, Any] = {
            "performance": PerformanceTester,
            "capability": CapabilityTester,
            "quality": QualityTester,
        }

        for tname in remaining_tests:
            _test_status["phase"] = tname
            cls = tester_classes.get(tname)
            if not cls:
                continue
            tester = cls(client)
            eligible = [m for m in available if not tester.skip_reason(m)]
            if not eligible:
                continue

            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                fut_map = {pool.submit(tester.test_model, m): m for m in eligible}
                for future in as_completed(fut_map):
                    model = fut_map[future]
                    try:
                        result = future.result()
                        _test_status["progress"] += 1
                        result_map[model.id].results[tname] = result
                        _test_status["model"] = model.id
                    except Exception as e:
                        _test_status["errors"].append(f"{model.id}/{tname}: {e}")

        # 生成报告
        _test_status["phase"] = "reporting"
        all_results = list(result_map.values())
        _test_status["results"] = all_results

        reporter = HTMLReporter()
        report_path = reporter.generate(all_results)
        _test_status["report_path"] = report_path
        _test_status["phase"] = "done"

    except Exception as e:
        _test_status["errors"].append(f"Fatal: {e}\n{traceback.format_exc()}")
    finally:
        _test_status["running"] = False


# ── Web server ───────────────────────────────────────────────────

_PAGE_HTML = r"""<!DOCTYPE html>
<html lang='zh-CN'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>NVIDIA Model Tester — 控制台</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:#0a0e14;color:#e2e8f0;min-height:100vh}
.container{max-width:900px;margin:0 auto;padding:24px}
.header{text-align:center;padding:32px 0 24px}
.header h1{font-size:28px;color:#76b900}
.header p{color:#8892a4;margin-top:8px;font-size:14px}
.card{background:#131926;border:1px solid #1e2a3a;border-radius:12px;
  padding:24px;margin-bottom:16px}
.card h2{font-size:16px;color:#76b900;margin-bottom:16px;display:flex;
  align-items:center;gap:8px}
.form-group{margin-bottom:16px}
.form-group label{display:block;font-size:13px;color:#8892a4;margin-bottom:6px;
  font-weight:500}
select[multiple]{width:100%;min-height:200px;background:#0a0e14;border:1px solid
  #1e2a3a;border-radius:8px;color:#e2e8f0;padding:8px;font-size:13px}
select[multiple] option{padding:6px 8px;border-radius:4px;margin:2px 0}
select[multiple] option:checked{background:#76b900;color:#000}
input[type=number]{width:120px;background:#0a0e14;border:1px solid #1e2a3a;
  border-radius:8px;color:#e2e8f0;padding:8px 12px;font-size:14px}
input[type=number]:focus{outline:none;border-color:#76b900}
.hint{font-size:11px;color:#8892a4;margin-top:4px}
.hint.warn{color:#e8a840}
.hint.error{color:#e84040}
.check-group{display:flex;flex-wrap:wrap;gap:12px}
.check-group label{display:flex;align-items:center;gap:6px;cursor:pointer;
  font-size:14px;color:#e2e8f0;padding:8px 16px;background:rgba(255,255,255,0.03);
  border:1px solid #1e2a3a;border-radius:8px;transition:all .2s}
.check-group label:hover{border-color:#76b900}
.check-group input[type=checkbox]{accent-color:#76b900;width:16px;height:16px}
.btn{width:100%;padding:12px;border:none;border-radius:8px;font-size:15px;
  font-weight:600;cursor:pointer;transition:all .2s}
.btn-run{background:#76b900;color:#000}
.btn-run:hover:not(:disabled){background:#8fd611}
.btn-run:disabled{background:#3a5c00;color:#666;cursor:not-allowed}
.btn-stop{background:#e84040;color:#fff;margin-top:8px}
.progress-bar{height:6px;background:#1e2a3a;border-radius:3px;margin-top:16px;
  overflow:hidden}
.progress-fill{height:100%;background:#76b900;border-radius:3px;transition:width .3s}
.status-line{font-size:12px;color:#8892a4;margin-top:8px;text-align:center}
.result-item{background:rgba(255,255,255,0.02);border:1px solid #1e2a3a;
  border-radius:8px;padding:12px;margin-bottom:8px}
.result-item .name{font-weight:600;color:#e2e8f0;margin-bottom:4px}
.result-item .score{font-size:24px;font-weight:700;color:#76b900}
.result-item .detail{font-size:11px;color:#8892a4;margin-top:4px}
.tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;
  margin-right:4px}
.tag.green{background:rgba(118,185,0,0.2);color:#76b900}
.tag.red{background:rgba(232,64,64,0.2);color:#e84040}
.link{color:#76b900;text-decoration:underline;font-size:13px}
#modelSearch{width:100%;background:#0a0e14;border:1px solid #1e2a3a;
  border-radius:8px;color:#e2e8f0;padding:8px 12px;font-size:13px;margin-bottom:8px}
#modelSearch:focus{outline:none;border-color:#76b900}
.select-actions{display:flex;gap:8px;margin-bottom:8px}
.select-actions button{background:rgba(255,255,255,0.05);border:1px solid #1e2a3a;
  color:#8892a4;padding:4px 12px;border-radius:6px;font-size:12px;cursor:pointer}
.select-actions button:hover{color:#e2e8f0;border-color:#76b900}
</style>
</head>
<body>
<div class='container'>
<div class='header'>
<h1>NVIDIA Model Tester</h1>
<p>Web Control Console — Select models, configure tests, and run</p>
</div>

<div class='card'>
<h2>1. Select Models</h2>
<input type='text' id='modelSearch' placeholder='Search/filter models...' oninput='filterModels()'>
<div class='select-actions'>
<button onclick='selectAll()'>Select All</button>
<button onclick='clearAll()'>Clear All</button>
<button onclick='selectCategory("llm")'>LLM Only</button>
<button onclick='selectCategory("multimodal")'>Multimodal Only</button>
<span id='selectedCount' style='font-size:12px;color:#8892a4;margin-left:auto'></span>
</div>
<select id='modelSelect' multiple></select>
</div>

<div class='card'>
<h2>2. Concurrency Settings</h2>
<div class='form-group'>
<label>Concurrent Threads</label>
<input type='number' id='concurrency' value='3' min='1' max='10'
  oninput='validateConcurrency()'>
<div class='hint' id='concurrencyHint'>
  NVIDIA NIM API limit: 40 requests/minute.
  Recommended: 2-4 (safe), 5-6 (moderate), 7+ (expect throttling).
</div>
</div>
</div>

<div class='card'>
<h2>3. Test Dimensions</h2>
<div class='check-group'>
<label><input type='checkbox' id='chk_availability' checked> Availability (Reachability)</label>
<label><input type='checkbox' id='chk_performance' checked> Performance (Latency/TTFT)</label>
<label><input type='checkbox' id='chk_capability' checked> Capability (12 Scenarios)</label>
<label><input type='checkbox' id='chk_quality'> Quality (LLM-as-Judge)</label>
</div>
<div class='hint' id='testsHint' style='margin-top:8px'></div>
</div>

<div class='card'>
<h2>4. Run</h2>
<button class='btn btn-run' id='runBtn' onclick='startTest()'>Start Test</button>
<button class='btn btn-stop' id='stopBtn' style='display:none'
  onclick='location.reload()'>Reset / Stop</button>
<div class='progress-bar' id='progressBar' style='display:none'>
<div class='progress-fill' id='progressFill' style='width:0%'></div>
</div>
<div class='status-line' id='statusLine'></div>
</div>

<div id='resultsSection' style='display:none'>
<div class='card'>
<h2>5. Results</h2>
<div id='resultsList'></div>
<a class='link' id='reportLink' href='#' target='_blank'>Open Full Report</a>
</div>
</div>
</div>

<script>
let allModels = [];
let pollingTimer = null;

async function loadModels() {
  try {
    const resp = await fetch('/api/models');
    const data = await resp.json();
    allModels = data.models || [];
    renderModelList(allModels);
  } catch(e) {
    document.getElementById('modelSelect').innerHTML =
      '<option disabled>Failed to load models. Check API key.</option>';
  }
}

function renderModelList(models) {
  const sel = document.getElementById('modelSelect');
  sel.innerHTML = '';
  models.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m.id;
    opt.textContent = `${m.id}  [${m.category}]`;
    sel.appendChild(opt);
  });
  updateCount();
}

function filterModels() {
  const q = document.getElementById('modelSearch').value.toLowerCase();
  const sel = document.getElementById('modelSelect');
  [...sel.options].forEach(opt => {
    opt.style.display = !q || opt.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

function selectAll() {
  [...document.getElementById('modelSelect').options].forEach(o => o.selected = true);
  updateCount();
}
function clearAll() {
  [...document.getElementById('modelSelect').options].forEach(o => o.selected = false);
  updateCount();
}
function selectCategory(cat) {
  const sel = document.getElementById('modelSelect');
  [...sel.options].forEach(o => {
    o.selected = o.textContent.includes(`[${cat}]`);
  });
  updateCount();
}
document.getElementById('modelSelect').addEventListener('change', updateCount);
function updateCount() {
  const n = document.getElementById('modelSelect').selectedOptions.length;
  document.getElementById('selectedCount').textContent = n + ' selected';
  updateTestsHint();
}

function validateConcurrency() {
  const v = parseInt(document.getElementById('concurrency').value) || 0;
  const hint = document.getElementById('concurrencyHint');
  if (v < 1) {
    hint.className = 'hint error';
    hint.textContent = 'Concurrency must be at least 1.';
  } else if (v <= 3) {
    hint.className = 'hint';
    hint.textContent = 'NVIDIA NIM API limit: 40 req/min. 1-3 threads: safe, minimal throttling.';
  } else if (v <= 5) {
    hint.className = 'hint warn';
    hint.textContent = 'NVIDIA NIM API limit: 40 req/min. 4-5 threads: moderate, occasional throttling.';
  } else {
    hint.className = 'hint error';
    hint.textContent = 'NVIDIA NIM API limit: 40 req/min. 6+ threads: high contention, expect frequent 429 delays.';
  }
  updateTestsHint();
}

function getSelectedTests() {
  const tests = [];
  if (document.getElementById('chk_availability').checked) tests.push('availability');
  if (document.getElementById('chk_performance').checked) tests.push('performance');
  if (document.getElementById('chk_capability').checked) tests.push('capability');
  if (document.getElementById('chk_quality').checked) tests.push('quality');
  return tests;
}

function updateTestsHint() {
  const n = document.getElementById('modelSelect').selectedOptions.length;
  const tests = getSelectedTests();
  const c = parseInt(document.getElementById('concurrency').value) || 1;
  if (n === 0 || tests.length === 0) {
    document.getElementById('testsHint').textContent = '';
    return;
  }
  // Rough estimate: availability=3 calls, performance=3, capability=12, quality=6
  const callsPerModel = {availability:3, performance:3, capability:12, quality:6};
  let totalCalls = 0;
  tests.forEach(t => { totalCalls += (callsPerModel[t] || 3) * n; });
  const estMinutes = Math.ceil(totalCalls / 35); // 35 req/min usable (40 - buffer)
  document.getElementById('testsHint').textContent =
    `Est. ~${totalCalls} API calls, ~${estMinutes} min at 35 req/min (threads=${c}).`;
}

// Kick off estimate on load
validateConcurrency();

async function startTest() {
  const selected = [...document.getElementById('modelSelect').selectedOptions].map(o => o.value);
  if (selected.length === 0) { alert('Please select at least one model.'); return; }
  const tests = getSelectedTests();
  if (tests.length === 0) { alert('Please select at least one test dimension.'); return; }
  const concurrency = parseInt(document.getElementById('concurrency').value) || 3;

  document.getElementById('runBtn').disabled = true;
  document.getElementById('runBtn').textContent = 'Running...';
  document.getElementById('stopBtn').style.display = 'block';
  document.getElementById('progressBar').style.display = 'block';
  document.getElementById('statusLine').textContent = 'Starting...';

  try {
    const resp = await fetch('/api/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({models: selected, concurrency, tests})
    });
    if (!resp.ok) throw new Error((await resp.json()).error || 'Failed to start');
    pollStatus();
  } catch(e) {
    document.getElementById('statusLine').textContent = 'Error: ' + e.message;
    document.getElementById('runBtn').disabled = false;
    document.getElementById('runBtn').textContent = 'Start Test';
  }
}

function pollStatus() {
  if (pollingTimer) clearInterval(pollingTimer);
  pollingTimer = setInterval(async () => {
    try {
      const resp = await fetch('/api/status');
      const data = await resp.json();
      const bar = document.getElementById('progressBar');
      const fill = document.getElementById('progressFill');
      const line = document.getElementById('statusLine');

      if (data.total > 0) {
        const pct = Math.round(data.progress / data.total * 100);
        fill.style.width = pct + '%';
        line.textContent = `Phase: ${data.phase} | Model: ${data.model} | ${data.progress}/${data.total}`;
      } else {
        line.textContent = `Phase: ${data.phase}`;
      }

      if (!data.running) {
        clearInterval(pollingTimer);
        pollingTimer = null;
        bar.style.display = 'none';
        document.getElementById('runBtn').disabled = false;
        document.getElementById('runBtn').textContent = 'Start Test';
        line.textContent = data.errors.length > 0
          ? `Done with ${data.errors.length} errors.`
          : 'Test complete!';
        showResults(data);
      }
    } catch(e) {
      clearInterval(pollingTimer);
      pollingTimer = null;
    }
  }, 1000);
}

function showResults(data) {
  const section = document.getElementById('resultsSection');
  section.style.display = 'block';
  const list = document.getElementById('resultsList');
  list.innerHTML = '';

  if (data.results && data.results.length > 0) {
    data.results.forEach(r => {
      const div = document.createElement('div');
      div.className = 'result-item';
      let tags = '';
      if (r.results) {
        Object.entries(r.results).forEach(([k, v]) => {
          const cls = v.passed ? 'green' : 'red';
          tags += `<span class='tag ${cls}'>${k}: ${(v.score*100).toFixed(0)}%</span>`;
        });
      }
      div.innerHTML = `<div class='name'>${r.model?.id || r.model_id || '?'}</div>
        <div class='score'>${(r.overall_score*100).toFixed(1)}%</div>
        <div class='detail'>${tags}</div>`;
      list.appendChild(div);
    });
  }

  if (data.report_path) {
    const link = document.getElementById('reportLink');
    link.href = '/api/report?path=' + encodeURIComponent(data.report_path);
    link.style.display = 'inline';
  }
  if (data.errors && data.errors.length > 0) {
    const errDiv = document.createElement('div');
    errDiv.style.cssText = 'color:#e84040;font-size:12px;margin-top:12px;';
    errDiv.textContent = 'Errors: ' + data.errors.slice(0, 5).join(' | ');
    list.appendChild(errDiv);
  }
}

loadModels();
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 抑制访问日志

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._send_html(_PAGE_HTML)

        elif path == "/api/models":
            try:
                client = NIMClient()
                from models.scanner import discover_models
                models = discover_models(client)
                self._send_json({
                    "models": [
                        {"id": m.id, "category": m.category, "name": m.name}
                        for m in models
                    ]
                })
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        elif path == "/api/status":
            self._send_json(_test_status)

        elif path == "/api/report":
            qs = parse_qs(parsed.query)
            path = qs.get("path", [""])[0]
            if path and os.path.isfile(path):
                with open(path, encoding="utf-8") as f:
                    self._send_html(f.read())
            else:
                self._send_json({"error": "Report not found"}, 404)

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/run":
            if _test_status["running"]:
                self._send_json({"error": "Test already running"}, 409)
                return

            content_len = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_len))

            model_ids = body.get("models", [])
            concurrency = body.get("concurrency", 3)
            tests = body.get("tests", ["availability", "performance", "capability"])

            if not model_ids:
                self._send_json({"error": "No models specified"}, 400)
                return
            if not tests:
                self._send_json({"error": "No tests specified"}, 400)
                return

            thread = threading.Thread(
                target=_run_test_async,
                args=(model_ids, concurrency, tests),
                daemon=True,
            )
            thread.start()
            self._send_json({"ok": True, "message": "Test started"})

        elif path == "/api/stop":
            _test_status["running"] = False
            self._send_json({"ok": True})

        else:
            self._send_json({"error": "Not found"}, 404)

    do_OPTIONS = do_GET  # 简化 CORS 预检


def main():
    parser = argparse.ArgumentParser(description="NVIDIA Model Tester Web UI")
    parser.add_argument("--port", type=int, default=8080, help="HTTP 端口 (默认: 8080)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="绑定地址 (默认: 127.0.0.1)")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), Handler)
    print(f"\n  NVIDIA Model Tester Web UI")
    print(f"  Open: http://{args.host}:{args.port}")
    print(f"  Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
