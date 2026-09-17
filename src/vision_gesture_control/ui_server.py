"""
UI Server implementation for vision-gesture-control.
Pure Python stdlib ThreadingHTTPServer serving Material 3 Vision Studio and REST APIs.
Zero external runtime dependencies.
"""

from __future__ import annotations

import cgi
import io
import json
import mimetypes
import os
import posixpath
import socket
import sys
import threading
import time
import urllib.parse
import zipfile
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple, Union

from .mcp_server import (
    calculate_dwell,
    classify_face,
    classify_gesture,
    generate_action_map,
    generate_mcp_client_config,
    get_diagnostics,
)

DEFAULT_PORT = 8088
DEFAULT_HOST = "0.0.0.0"
SERVER_VERSION = "1.0.0"
SERVER_START_TIME = time.time()

# ---------------------------------------------------------------------------
# Built-in Google Material 3 Vision Studio HTML Fallback
# ---------------------------------------------------------------------------

FALLBACK_INDEX_HTML = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Google Material 3 Vision Studio | Vision Gesture Control</title>
  <meta name="description" content="Local-first Vision Gesture Control & Dwell Studio powered by MCP">
  <style>
    :root {
      --md-sys-color-primary: #a8c7fa;
      --md-sys-color-on-primary: #062e6f;
      --md-sys-color-primary-container: #0842a0;
      --md-sys-color-on-primary-container: #d3e3fd;
      --md-sys-color-surface: #111318;
      --md-sys-color-surface-dim: #111318;
      --md-sys-color-surface-bright: #37393e;
      --md-sys-color-surface-container-lowest: #0c0e13;
      --md-sys-color-surface-container-low: #191c20;
      --md-sys-color-surface-container: #1d2024;
      --md-sys-color-surface-container-high: #282a2f;
      --md-sys-color-surface-container-highest: #33353a;
      --md-sys-color-on-surface: #e2e2e9;
      --md-sys-color-on-surface-variant: #c4c6d0;
      --md-sys-color-outline: #8e9099;
      --md-sys-color-outline-variant: #44474f;
      --md-sys-color-secondary-container: #334460;
      --md-sys-color-on-secondary-container: #d3e3fd;
      --md-sys-color-tertiary: #6dd58c;
      --md-sys-color-error: #f2b8b5;
      --md-sys-shape-corner-small: 8px;
      --md-sys-shape-corner-medium: 12px;
      --md-sys-shape-corner-large: 16px;
      --md-sys-shape-corner-full: 9999px;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--md-sys-color-surface);
      color: var(--md-sys-color-on-surface);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Google Sans", Helvetica, Arial, sans-serif;
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    header {
      background-color: var(--md-sys-color-surface-container);
      border-bottom: 1px solid var(--md-sys-color-outline-variant);
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 1.15rem;
      font-weight: 600;
      color: var(--md-sys-color-on-surface);
    }
    .brand-badge {
      background-color: var(--md-sys-color-primary-container);
      color: var(--md-sys-color-on-primary-container);
      font-size: 0.75rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: var(--md-sys-shape-corner-full);
      letter-spacing: 0.5px;
    }

    .nav-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    button, .btn {
      background-color: var(--md-sys-color-surface-container-highest);
      color: var(--md-sys-color-on-surface);
      border: 1px solid var(--md-sys-color-outline-variant);
      padding: 8px 16px;
      border-radius: var(--md-sys-shape-corner-full);
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
      text-decoration: none;
    }
    button:hover, .btn:hover {
      background-color: var(--md-sys-color-primary-container);
      color: var(--md-sys-color-on-primary-container);
      border-color: var(--md-sys-color-primary);
    }
    button.primary, .btn.primary {
      background-color: var(--md-sys-color-primary);
      color: var(--md-sys-color-on-primary);
      border-color: transparent;
    }
    button.primary:hover, .btn.primary:hover {
      opacity: 0.9;
    }

    main {
      flex: 1;
      padding: 24px;
      max-width: 1440px;
      margin: 0 auto;
      width: 100%;
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 24px;
    }

    @media (max-width: 960px) {
      main { grid-template-columns: 1fr; }
    }

    .card {
      background-color: var(--md-sys-color-surface-container);
      border: 1px solid var(--md-sys-color-outline-variant);
      border-radius: var(--md-sys-shape-corner-large);
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--md-sys-color-outline-variant);
      padding-bottom: 12px;
    }
    .card-title {
      font-size: 1rem;
      font-weight: 600;
      color: var(--md-sys-color-on-surface);
    }

    /* Video & Canvas viewport */
    .viewport-container {
      position: relative;
      width: 100%;
      height: 380px;
      background-color: var(--md-sys-color-surface-container-lowest);
      border-radius: var(--md-sys-shape-corner-medium);
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid var(--md-sys-color-outline-variant);
    }
    .viewport-canvas {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .viewport-overlay {
      position: absolute;
      top: 12px;
      left: 12px;
      right: 12px;
      display: flex;
      justify-content: space-between;
      pointer-events: none;
    }
    .live-chip {
      background-color: rgba(17, 19, 24, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid var(--md-sys-color-outline-variant);
      padding: 4px 10px;
      border-radius: var(--md-sys-shape-corner-full);
      font-size: 0.75rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .live-dot {
      width: 8px;
      height: 8px;
      background-color: var(--md-sys-color-tertiary);
      border-radius: 50%;
      animation: pulse 1.5s infinite ease-in-out;
    }
    @keyframes pulse {
      0%, 100% { transform: scale(1); opacity: 1; }
      50% { transform: scale(1.3); opacity: 0.6; }
    }

    /* Dwell interactive demo target */
    .dwell-target-box {
      width: 100%;
      height: 100px;
      border: 2px dashed var(--md-sys-color-primary);
      border-radius: var(--md-sys-shape-corner-medium);
      background-color: rgba(168, 199, 250, 0.05);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      cursor: crosshair;
      position: relative;
      overflow: hidden;
    }
    .dwell-progress-bar {
      position: absolute;
      bottom: 0;
      left: 0;
      height: 6px;
      background-color: var(--md-sys-color-tertiary);
      width: 0%;
      transition: width 0.1s linear;
    }

    .metric-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }
    .metric-box {
      background-color: var(--md-sys-color-surface-container-high);
      padding: 12px;
      border-radius: var(--md-sys-shape-corner-medium);
      border: 1px solid var(--md-sys-color-outline-variant);
    }
    .metric-label {
      font-size: 0.75rem;
      color: var(--md-sys-color-on-surface-variant);
      margin-bottom: 4px;
    }
    .metric-value {
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--md-sys-color-on-surface);
    }

    /* Presets Table */
    .preset-select {
      background-color: var(--md-sys-color-surface-container-high);
      color: var(--md-sys-color-on-surface);
      border: 1px solid var(--md-sys-color-outline-variant);
      padding: 8px 12px;
      border-radius: var(--md-sys-shape-corner-medium);
      font-size: 0.85rem;
      width: 100%;
    }
    .bindings-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 260px;
      overflow-y: auto;
    }
    .binding-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 12px;
      background-color: var(--md-sys-color-surface-container-high);
      border-radius: var(--md-sys-shape-corner-small);
      font-size: 0.82rem;
    }
    .key-badge {
      background-color: var(--md-sys-color-surface-container-highest);
      border: 1px solid var(--md-sys-color-outline);
      padding: 2px 8px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 0.78rem;
    }

    /* Code block */
    pre, code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.8rem;
    }
    pre {
      background-color: var(--md-sys-color-surface-container-lowest);
      border: 1px solid var(--md-sys-color-outline-variant);
      padding: 12px;
      border-radius: var(--md-sys-shape-corner-medium);
      overflow-x: auto;
      max-height: 180px;
    }

    footer {
      background-color: var(--md-sys-color-surface-container);
      border-top: 1px solid var(--md-sys-color-outline-variant);
      padding: 16px 24px;
      text-align: center;
      font-size: 0.8rem;
      color: var(--md-sys-color-on-surface-variant);
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--md-sys-color-primary)"><path d="M18 11V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v0"/><path d="M14 10V4a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v2"/><path d="M10 10.5V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v8"/><path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/></svg>
      <span>Google Material 3 Vision Studio</span>
      <span class="brand-badge">MCP v1.0.0</span>
    </div>
    <div class="nav-actions">
      <button id="btn-export-bundle" onclick="downloadBundle()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        Export Bundle (ZIP)
      </button>
      <button class="primary" onclick="showMcpModal()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="M4.93 19.07l2.83-2.83"/><path d="M16.24 7.76l2.83-2.83"/></svg>
        MCP Config
      </button>
    </div>
  </header>

  <main>
    <!-- Left Column: Vision Tracking & Dwell Zone -->
    <div style="display: flex; flex-direction: column; gap: 24px;">
      <div class="card">
        <div class="card-header">
          <span class="card-title">Live Vision Gesture Tracking</span>
          <span class="live-chip"><span class="live-dot"></span> Engine Online</span>
        </div>

        <div class="viewport-container" id="viewport">
          <div class="viewport-overlay">
            <span class="live-chip" id="overlay-gesture">Gesture: Open Palm</span>
            <span class="live-chip" id="overlay-fps">60 FPS</span>
          </div>
          <canvas id="vision-canvas" class="viewport-canvas"></canvas>
        </div>

        <div class="metric-grid">
          <div class="metric-box">
            <div class="metric-label">Detected Gesture</div>
            <div class="metric-value" id="val-gesture" style="color:var(--md-sys-color-primary)">open_palm</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">Confidence</div>
            <div class="metric-value" id="val-confidence">98%</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">Pinch State</div>
            <div class="metric-value" id="val-pinch" style="color:var(--md-sys-color-tertiary)">Open (0.65)</div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">Interactive Dwell Progress Zone</span>
          <span class="live-chip">Hover Inside Box</span>
        </div>
        <div class="dwell-target-box" id="dwell-target" onmousemove="handleDwellMove(event)" onmouseleave="handleDwellLeave()">
          <span style="font-size:0.9rem; font-weight:600; z-index:2;" id="dwell-text">Hover here to trigger Dwell Click (1000ms)</span>
          <div class="dwell-progress-bar" id="dwell-bar"></div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:var(--md-sys-color-on-surface-variant);">
          <span>State: <strong id="dwell-state-lbl">idle</strong></span>
          <span>Progress: <strong id="dwell-pct-lbl">0%</strong></span>
        </div>
      </div>
    </div>

    <!-- Right Column: Presets, Telemetry, and MCP Integration -->
    <div style="display: flex; flex-direction: column; gap: 24px;">
      <div class="card">
        <div class="card-header">
          <span class="card-title">Gesture Action Map Presets</span>
        </div>
        <select class="preset-select" id="preset-dropdown" onchange="loadPreset(this.value)">
          <option value="presentation">Presentation Mode (Keynote / Slides)</option>
          <option value="media">Media Player Control (Spotify / YouTube)</option>
          <option value="drawing">Canvas & Drawing Studio (Excalidraw / Figma)</option>
          <option value="gaming">Air Gaming Controller (Retro / Arcade)</option>
          <option value="accessibility">Accessibility & Headless Dwell Navigation</option>
        </select>

        <div class="bindings-list" id="bindings-list">
          <!-- Populated by JS -->
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">MCP Client Configuration</span>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="btn" style="padding:4px 10px; font-size:0.75rem;" onclick="fetchMcpConfig('claude_desktop')">Claude Desktop</button>
          <button class="btn" style="padding:4px 10px; font-size:0.75rem;" onclick="fetchMcpConfig('cursor')">Cursor</button>
          <button class="btn" style="padding:4px 10px; font-size:0.75rem;" onclick="fetchMcpConfig('cline')">Cline</button>
          <button class="btn" style="padding:4px 10px; font-size:0.75rem;" onclick="fetchMcpConfig('zed')">Zed</button>
        </div>
        <pre><code id="mcp-config-code">Loading config...</code></pre>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">System & Telemetry Diagnostics</span>
          <button class="btn" style="padding:2px 8px; font-size:0.75rem;" onclick="loadDiagnostics()">Refresh</button>
        </div>
        <div id="diagnostics-summary" style="font-size:0.82rem; color:var(--md-sys-color-on-surface-variant); display:flex; flex-direction:column; gap:4px;">
          <span>Loading telemetry...</span>
        </div>
      </div>
    </div>
  </main>

  <footer>
    <p>Google Material 3 Vision Studio &bull; Pure Python Stdlib &bull; Zero External Dependencies &bull; MCP Protocol v2024-11-05</p>
  </footer>

  <script>
    let dwellStartTime = null;
    let dwellTimer = null;

    async function loadPreset(presetName) {
      try {
        const res = await fetch(`/api/presets?preset=${presetName}`);
        const data = await res.json();
        const preset = data[presetName] || data;
        const container = document.getElementById('bindings-list');
        container.innerHTML = '';

        if (preset && preset.bindings) {
          for (const [gesture, info] of Object.entries(preset.bindings)) {
            const row = document.createElement('div');
            row.className = 'binding-row';
            row.innerHTML = `
              <div>
                <strong>${gesture.replace('_', ' ').toUpperCase()}</strong>
                <div style="font-size:0.75rem; color:var(--md-sys-color-on-surface-variant);">${info.description}</div>
              </div>
              <span class="key-badge">${info.key || info.action}</span>
            `;
            container.appendChild(row);
          }
        }
      } catch (err) {
        console.error('Failed to load preset:', err);
      }
    }

    async function fetchMcpConfig(client) {
      try {
        const res = await fetch(`/api/mcp/config?client=${client}`);
        const data = await res.json();
        document.getElementById('mcp-config-code').textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        document.getElementById('mcp-config-code').textContent = 'Error loading MCP config: ' + err;
      }
    }

    async function loadDiagnostics() {
      try {
        const res = await fetch('/api/diagnostics');
        const diag = await res.json();
        const container = document.getElementById('diagnostics-summary');
        container.innerHTML = `
          <div><strong>OS:</strong> ${diag.system.os} (${diag.system.release}) - ${diag.system.machine}</div>
          <div><strong>Display Server:</strong> ${diag.system.display_server}</div>
          <div><strong>Python:</strong> ${diag.python.version} (${diag.python.implementation})</div>
          <div><strong>Cameras Detected:</strong> ${diag.hardware.cameras_detected}</div>
          <div><strong>CPU Cores:</strong> ${diag.hardware.cpu_count}</div>
        `;
      } catch (err) {
        console.error('Diagnostics error:', err);
      }
    }

    function handleDwellMove(e) {
      const rect = e.currentTarget.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;

      if (!dwellStartTime) {
        dwellStartTime = performance.now();
      }

      const elapsed = performance.now() - dwellStartTime;
      const duration = 1000.0;
      const progress = Math.min(1.0, elapsed / duration);
      const pct = Math.round(progress * 100);

      document.getElementById('dwell-bar').style.width = pct + '%';
      document.getElementById('dwell-pct-lbl').textContent = pct + '%';

      if (progress >= 1.0) {
        document.getElementById('dwell-state-lbl').textContent = 'completed (CLICK!)';
        document.getElementById('dwell-text').textContent = '🎉 DWELL TRIGGERED!';
      } else {
        document.getElementById('dwell-state-lbl').textContent = 'dwelling...';
        document.getElementById('dwell-text').textContent = `Dwelling: ${Math.round(elapsed)}ms / 1000ms`;
      }
    }

    function handleDwellLeave() {
      dwellStartTime = null;
      document.getElementById('dwell-bar').style.width = '0%';
      document.getElementById('dwell-pct-lbl').textContent = '0%';
      document.getElementById('dwell-state-lbl').textContent = 'idle';
      document.getElementById('dwell-text').textContent = 'Hover here to trigger Dwell Click (1000ms)';
    }

    function downloadBundle() {
      window.location.href = '/api/export-bundle';
    }

    function showMcpModal() {
      fetchMcpConfig('claude_desktop');
    }

    // Initialize on load
    window.addEventListener('DOMContentLoaded', () => {
      loadPreset('presentation');
      fetchMcpConfig('claude_desktop');
      loadDiagnostics();
    });
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# HTTP Request Handler with REST API & Static Asset Dispatcher
# ---------------------------------------------------------------------------

class VisionUIRequestHandler(SimpleHTTPRequestHandler):
    """
    HTTP Request Handler serving Material 3 Vision Studio UI and REST endpoints.
    """

    server_version = f"VisionGestureStudio/{SERVER_VERSION}"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Directory from which to serve static files
        self.public_dir = getattr(self, "public_dir", None) or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "public")
        )
        super().__init__(*args, **kwargs)

    def _set_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

    def _send_json(self, data: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_error_json(self, message: str, status: int = HTTPStatus.BAD_REQUEST) -> None:
        self._send_json({"error": message, "status": status}, status=status)

    def _parse_json_body(self) -> Optional[Dict[str, Any]]:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                return {}
            body_bytes = self.rfile.read(content_length)
            return json.loads(body_bytes.decode("utf-8"))
        except Exception:
            return None

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        query = urllib.parse.parse_qs(parsed_url.query)

        # -------------------------------------------------------------------
        # REST API Routes
        # -------------------------------------------------------------------
        if path == "/api/health":
            self._send_json({
                "status": "ok",
                "version": SERVER_VERSION,
                "uptime_seconds": round(time.time() - SERVER_START_TIME, 2),
                "service": "vision-gesture-control",
            })
            return

        elif path == "/api/presets":
            preset_name = query.get("preset", ["all"])[0]
            if preset_name in ("presentation", "media", "media_player", "drawing", "gaming", "accessibility"):
                self._send_json(generate_action_map(preset_name))
            else:
                self._send_json({
                    "presentation": generate_action_map("presentation"),
                    "media": generate_action_map("media"),
                    "drawing": generate_action_map("drawing"),
                    "gaming": generate_action_map("gaming"),
                    "accessibility": generate_action_map("accessibility"),
                })
            return

        elif path == "/api/mcp/config":
            client_name = query.get("client", ["claude_desktop"])[0]
            python_path = query.get("python", ["python3"])[0]
            self._send_json(generate_mcp_client_config(client_name, python_path))
            return

        elif path == "/api/diagnostics":
            extended = query.get("extended", ["false"])[0].lower() in ("true", "1")
            self._send_json(get_diagnostics(extended=extended))
            return

        elif path == "/api/export-bundle":
            # Allow GET download of export bundle as well
            self._handle_export_bundle()
            return

        elif path == "/favicon.ico":
            ico_path = os.path.join(self.public_dir, "favicon.ico")
            if os.path.isfile(ico_path):
                self._serve_file(ico_path, "image/x-icon")
            else:
                self.send_response(HTTPStatus.NO_CONTENT)
                self.end_headers()
            return

        # -------------------------------------------------------------------
        # Static Assets & Fallback Material 3 HTML Studio
        # -------------------------------------------------------------------
        # Normalize request path for static file serving
        target_path = parsed_url.path.lstrip("/")
        if target_path == "" or target_path == "index.html":
            # Check if custom public/index.html exists
            custom_index = os.path.join(self.public_dir, "index.html")
            if os.path.isfile(custom_index):
                self._serve_file(custom_index, "text/html; charset=utf-8")
                return
            else:
                # Serve built-in Material 3 Studio HTML
                body = FALLBACK_INDEX_HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(body)
                return

        # Check in public_dir for other static assets
        safe_rel_path = posixpath.normpath(target_path)
        disk_path = os.path.join(self.public_dir, safe_rel_path)
        if os.path.isfile(disk_path):
            mime_type, _ = mimetypes.guess_type(disk_path)
            self._serve_file(disk_path, mime_type or "application/octet-stream")
            return

        # 404 Not Found
        self._send_error_json(f"File or endpoint not found: {self.path}", status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path.rstrip("/")

        if path == "/api/classify":
            body = self._parse_json_body()
            if body is None:
                self._send_error_json("Invalid JSON payload", HTTPStatus.BAD_REQUEST)
                return

            landmarks = body.get("landmarks", [])
            handedness = body.get("handedness", "Right")
            confidence_thresh = float(body.get("confidence_threshold", 0.5))
            result = classify_gesture(landmarks, handedness, confidence_thresh)
            self._send_json(result)
            return

        elif path == "/api/dwell":
            body = self._parse_json_body()
            if body is None:
                self._send_error_json("Invalid JSON payload", HTTPStatus.BAD_REQUEST)
                return

            x = float(body.get("x", 0.0))
            y = float(body.get("y", 0.0))
            zone = body.get("zone", {})
            duration_ms = float(body.get("duration_ms", 1000.0))
            elapsed_ms = float(body.get("elapsed_ms", 0.0))
            result = calculate_dwell(x, y, zone, duration_ms, elapsed_ms)
            self._send_json(result)
            return

        elif path == "/api/face":
            body = self._parse_json_body()
            if body is None:
                self._send_error_json("Invalid JSON payload", HTTPStatus.BAD_REQUEST)
                return

            face_landmarks = body.get("face_landmarks", None) or body
            result = classify_face(face_landmarks)
            self._send_json(result)
            return

        elif path == "/api/export-bundle":
            self._handle_export_bundle()
            return

        else:
            self._send_error_json(f"POST endpoint not found: {self.path}", HTTPStatus.NOT_FOUND)

    def _serve_file(self, filepath: str, content_type: str) -> None:
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self._set_cors_headers()
            self.end_headers()
            try:
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError):
                pass
        except Exception as e:
            self._send_error_json(f"Failed to read file: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_export_bundle(self) -> None:
        """
        Creates an in-memory ZIP archive of the standalone Vision Gesture Studio app
        and streams it back as application/zip.
        """
        try:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                # 1. HTML Studio
                custom_index = os.path.join(self.public_dir, "index.html")
                if os.path.isfile(custom_index):
                    with open(custom_index, "r", encoding="utf-8") as f:
                        html_content = f.read()
                else:
                    html_content = FALLBACK_INDEX_HTML

                zf.writestr("index.html", html_content)

                # 2. Web App Manifest
                manifest = {
                    "name": "Google Material 3 Vision Studio",
                    "short_name": "Vision Studio",
                    "description": "Zero-dependency Vision Gesture Control Studio",
                    "start_url": "./index.html",
                    "display": "standalone",
                    "background_color": "#111318",
                    "theme_color": "#a8c7fa",
                    "icons": [],
                }
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))

                # 3. Action Maps Preset JSON
                all_presets = {
                    "presentation": generate_action_map("presentation"),
                    "media": generate_action_map("media"),
                    "drawing": generate_action_map("drawing"),
                    "gaming": generate_action_map("gaming"),
                    "accessibility": generate_action_map("accessibility"),
                }
                zf.writestr("action_maps.json", json.dumps(all_presets, indent=2))

                # 4. MCP Configs
                mcp_configs = generate_mcp_client_config("all")
                zf.writestr("mcp_configs.json", json.dumps(mcp_configs, indent=2))

                # 5. README.md
                readme_text = """# Vision Gesture Studio Standalone

This bundle contains the standalone Google Material 3 Vision Studio.
Simply open `index.html` in any modern web browser to run locally with zero server requirements!

## Features
- Pure WebGL & MediaPipe Hands tracker
- Real-time gesture classification
- Dwell time interactive navigation
- Action maps for Keynote, Spotify, Excalidraw, and OS accessibility
"""
                zf.writestr("README.md", readme_text)

            zip_data = zip_buffer.getvalue()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", 'attachment; filename="vision-gesture-studio-standalone.zip"')
            self.send_header("Content-Length", str(len(zip_data)))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(zip_data)

        except Exception as e:
            self._send_error_json(f"Failed to create export bundle: {str(e)}", HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy standard request logs during testing unless DEBUG is set
        if os.environ.get("VISION_DEBUG"):
            super().log_message(format, *args)


# ---------------------------------------------------------------------------
# UIServer Wrapper Class
# ---------------------------------------------------------------------------

class CustomThreadingHTTPServer(ThreadingHTTPServer):
    """Custom ThreadingHTTPServer with custom public_dir."""
    public_dir: str = ""


class UIServer:
    """
    Manager for the Vision Gesture Control Web Studio HTTP Server.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        public_dir: Optional[str] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.public_dir = public_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "public")
        )
        self.server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Starts the HTTP server on a background daemon thread."""
        handler_cls = VisionUIRequestHandler
        handler_cls.public_dir = self.public_dir  # type: ignore

        # Attempt binding to requested port; if 0, OS selects open port
        self.server = CustomThreadingHTTPServer((self.host, self.port), handler_cls)
        self.server.public_dir = self.public_dir
        # Update port in case port 0 was passed
        self.port = self.server.server_address[1]

        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Gracefully shuts down the server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None

    def get_url(self) -> str:
        host = "localhost" if self.host in ("0.0.0.0", "") else self.host
        return f"http://{host}:{self.port}"


def create_ui_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    public_dir: Optional[str] = None,
) -> UIServer:
    """Factory helper to create and start a UIServer instance."""
    server = UIServer(host=host, port=port, public_dir=public_dir)
    server.start()
    return server


def run_ui_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    public_dir: Optional[str] = None,
) -> None:
    """Runs the HTTP server synchronously until interrupted."""
    server = UIServer(host=host, port=port, public_dir=public_dir)
    server.start()
    print(f"🌟 Google Material 3 Vision Studio running at {server.get_url()}")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.stop()
