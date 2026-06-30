#!/usr/bin/env python3
"""
Tutorial Viewer — A local web viewer for generated codebase tutorials.

Usage:
    python viewer.py                  # View all projects in output/
    python viewer.py --port 8080      # Use a custom port
    python viewer.py --dir output     # Specify output directory

Opens a browser with a navigable, rendered view of the markdown tutorials.
"""

import http.server
import json
import os
import re
import argparse
import webbrowser
import urllib.parse
from pathlib import Path

OUTPUT_DIR = "output"

# ─── HTML Shell ───────────────────────────────────────────────────────────────

HTML_SHELL = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tutorial Viewer</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --sidebar-w: 300px;
  --header-h: 60px;
  --radius: 10px;
  --transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ── Dark Theme (default) ───────────────────────────────────── */
[data-theme='dark'], :root:not([data-theme]) {
  --bg-primary: #0f1117;
  --bg-secondary: #161822;
  --bg-tertiary: #1c1f2e;
  --bg-hover: #252940;
  --bg-active: #2d3250;
  --header-bg: rgba(15, 17, 23, 0.8);
  --border: #2a2d3e;
  --border-accent: #4f46e5;
  --text-primary: #e2e4ed;
  --text-secondary: #9094a6;
  --text-muted: #5d6175;
  --accent: #818cf8;
  --accent-glow: rgba(129, 140, 248, 0.15);
  --accent-bright: #a5b4fc;
  --green: #34d399;
  --amber: #fbbf24;
  --rose: #fb7185;
  --code-bg: #1a1d2e;
}

/* ── Light Theme ────────────────────────────────────────────── */
[data-theme='light'] {
  --bg-primary: #f8f9fc;
  --bg-secondary: #ffffff;
  --bg-tertiary: #f0f1f5;
  --bg-hover: #e8e9f0;
  --bg-active: #dcdee8;
  --header-bg: rgba(255, 255, 255, 0.85);
  --border: #d5d7e2;
  --border-accent: #4f46e5;
  --text-primary: #1a1c2e;
  --text-secondary: #5c5f73;
  --text-muted: #9295a5;
  --accent: #4f46e5;
  --accent-glow: rgba(79, 70, 229, 0.08);
  --accent-bright: #4338ca;
  --green: #059669;
  --amber: #d97706;
  --rose: #e11d48;
  --code-bg: #eef0f5;
}

html { font-size: 15px; scroll-behavior: smooth; }
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.7;
  overflow: hidden;
  height: 100vh;
}

/* ── Header ─────────────────────────────────────────────────── */
header {
  position: fixed; top: 0; left: 0; right: 0;
  height: var(--header-h);
  background: var(--header-bg);
  backdrop-filter: blur(20px) saturate(1.5);
  -webkit-backdrop-filter: blur(20px) saturate(1.5);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 24px;
  z-index: 100;
  gap: 16px;
}
header .spacer { flex: 1; }

/* ── Theme Toggle ───────────────────────────────────────────── */
.theme-toggle {
  display: flex; align-items: center; gap: 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: 24px;
  padding: 4px;
  cursor: pointer;
  transition: all var(--transition);
}
.theme-toggle:hover { border-color: var(--accent); }
.theme-toggle .toggle-option {
  display: flex; align-items: center; justify-content: center;
  width: 30px; height: 26px;
  border-radius: 20px;
  font-size: 0.85rem;
  transition: all var(--transition);
  color: var(--text-muted);
}
.theme-toggle .toggle-option.active {
  background: var(--accent);
  color: #fff;
  box-shadow: 0 2px 8px rgba(129, 140, 248, 0.3);
}
[data-theme='light'] .theme-toggle .toggle-option.active {
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
}
header .logo {
  font-weight: 700; font-size: 1.15rem;
  background: linear-gradient(135deg, var(--accent), var(--accent-bright));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  letter-spacing: -0.02em;
  white-space: nowrap;
}
header .logo span { font-weight: 400; opacity: 0.6; -webkit-text-fill-color: var(--text-secondary); margin-left: 4px; }
#projectSelect {
  background: var(--bg-tertiary); color: var(--text-primary);
  border: 1px solid var(--border); border-radius: 8px;
  padding: 6px 12px; font-size: 0.85rem; font-family: inherit;
  cursor: pointer; outline: none;
  transition: border var(--transition);
  max-width: 260px;
}
#projectSelect:focus { border-color: var(--accent); }

/* ── Layout ─────────────────────────────────────────────────── */
.app {
  display: flex;
  margin-top: var(--header-h);
  height: calc(100vh - var(--header-h));
}

/* ── Sidebar ────────────────────────────────────────────────── */
.sidebar {
  width: var(--sidebar-w); min-width: var(--sidebar-w);
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  overflow-y: auto; padding: 16px 0;
  transition: transform 0.3s ease;
}
.sidebar::-webkit-scrollbar { width: 4px; }
.sidebar::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
.sidebar .section-label {
  font-size: 0.65rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.1em; color: var(--text-muted);
  padding: 12px 20px 6px;
}
.sidebar a {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 9px 20px; text-decoration: none; color: var(--text-secondary);
  font-size: 0.85rem; font-weight: 400;
  border-left: 3px solid transparent;
  transition: all var(--transition);
  cursor: pointer;
}
.sidebar a:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
.sidebar a.active {
  background: var(--accent-glow);
  color: var(--accent-bright);
  border-left-color: var(--accent);
  font-weight: 500;
}
.sidebar a .ch-num {
  font-size: 0.7rem; font-weight: 600;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  border-radius: 4px;
  min-width: 22px; height: 20px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
  transition: all var(--transition);
}
.sidebar a.active .ch-num {
  background: var(--accent);
  color: var(--bg-primary);
}

/* ── Content ────────────────────────────────────────────────── */
.content {
  flex: 1; overflow-y: auto; padding: 48px 64px 120px;
  scroll-behavior: smooth;
}
.content::-webkit-scrollbar { width: 6px; }
.content::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

/* ── Welcome ────────────────────────────────────────────────── */
.welcome {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; min-height: 60vh;
  text-align: center; animation: fadeUp 0.5s ease;
}
.welcome h1 {
  font-size: 2.4rem; font-weight: 700; letter-spacing: -0.03em;
  background: linear-gradient(135deg, var(--accent), var(--accent-bright), var(--green));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  margin-bottom: 12px;
}
.welcome p { color: var(--text-secondary); font-size: 1.05rem; max-width: 500px; }

/* ── Markdown Styles ────────────────────────────────────────── */
.md-body { max-width: 100%; animation: fadeUp 0.35s ease; }
.md-body h1 {
  font-size: 2rem; font-weight: 700; letter-spacing: -0.03em;
  margin: 0 0 8px; padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(135deg, var(--text-primary), var(--accent-bright));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.md-body h2 {
  font-size: 1.35rem; font-weight: 600; margin: 40px 0 12px;
  color: var(--accent-bright); letter-spacing: -0.01em;
}
.md-body h3 {
  font-size: 1.1rem; font-weight: 600; margin: 32px 0 8px;
  color: var(--text-primary);
}
.md-body h4 { font-size: 0.95rem; font-weight: 600; margin: 24px 0 6px; color: var(--text-secondary); }
.md-body p { margin: 12px 0; color: var(--text-primary); }
.md-body a { color: var(--accent); text-decoration: none; border-bottom: 1px solid transparent; transition: border var(--transition); }
.md-body a:hover { border-bottom-color: var(--accent); }
.md-body strong { font-weight: 600; color: var(--text-primary); }
.md-body em { color: var(--text-secondary); }
.md-body ul, .md-body ol { margin: 12px 0; padding-left: 24px; }
.md-body li { margin: 6px 0; color: var(--text-primary); }
.md-body li::marker { color: var(--accent); }
.md-body blockquote {
  border-left: 3px solid var(--accent);
  margin: 16px 0; padding: 8px 16px;
  background: var(--accent-glow);
  border-radius: 0 var(--radius) var(--radius) 0;
  color: var(--text-secondary);
}
.md-body hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }
.md-body img { max-width: 100%; border-radius: var(--radius); margin: 16px 0; }
.md-body table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.9rem; }
.md-body th {
  text-align: left; padding: 10px 14px; font-weight: 600;
  background: var(--bg-tertiary); border-bottom: 2px solid var(--border);
  color: var(--accent-bright); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em;
}
.md-body td { padding: 10px 14px; border-bottom: 1px solid var(--border); }
.md-body tr:hover td { background: var(--bg-hover); }

/* Inline code */
.md-body code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85em; padding: 2px 7px;
  background: var(--code-bg); border-radius: 5px;
  color: var(--accent-bright);
  border: 1px solid var(--border);
}
/* Code blocks */
.md-body pre {
  margin: 16px 0; border-radius: var(--radius);
  background: var(--code-bg); border: 1px solid var(--border);
  overflow-x: auto; position: relative;
}
.md-body pre code {
  display: block; padding: 20px;
  background: none; border: none; border-radius: 0;
  color: var(--text-primary); font-size: 0.82rem;
  line-height: 1.65;
}

/* Mermaid diagrams */
.md-body .mermaid {
  background: var(--bg-tertiary);
  border-radius: var(--radius);
  padding: 24px; margin: 16px 0;
  border: 1px solid var(--border);
  text-align: center;
}

/* Chapter nav at bottom */
.chapter-nav {
  display: flex; gap: 16px; margin-top: 64px;
  padding-top: 24px; border-top: 1px solid var(--border);
}
.chapter-nav a {
  flex: 1; display: block; padding: 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border); border-radius: var(--radius);
  text-decoration: none; color: var(--text-secondary);
  transition: all var(--transition);
  font-size: 0.85rem;
}
.chapter-nav a:hover { border-color: var(--accent); background: var(--accent-glow); color: var(--text-primary); }
.chapter-nav a .label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); margin-bottom: 4px; }
.chapter-nav .next { text-align: right; }

/* ── Animations ─────────────────────────────────────────────── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Responsive ─────────────────────────────────────────────── */
@media (max-width: 900px) {
  .sidebar { position: fixed; left: 0; top: var(--header-h); bottom: 0; z-index: 50; transform: translateX(-100%); }
  .sidebar.open { transform: translateX(0); box-shadow: 4px 0 30px rgba(0,0,0,0.5); }
  .content { padding: 32px 24px 100px; }
  .md-body h1 { font-size: 1.5rem; }
}
</style>
</head>
<body>

<header>
  <div class="logo">Tutorial Viewer <span>by PocketFlow</span></div>
  <select id="projectSelect"></select>
  <div class="spacer"></div>
  <div class="theme-toggle" id="themeToggle" title="Toggle light/dark mode">
    <span class="toggle-option" data-theme="light">☀️</span>
    <span class="toggle-option active" data-theme="dark">🌙</span>
  </div>
</header>

<div class="app">
  <nav class="sidebar" id="sidebar"></nav>
  <main class="content" id="content">
    <div class="welcome">
      <h1>Codebase Tutorials</h1>
      <p>Select a project and chapter from the sidebar to start reading.</p>
    </div>
  </main>
</div>

<!-- Markdown parser (marked.js) + mermaid -->
<script src="https://cdn.jsdelivr.net/npm/marked@14/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>
const $ = s => document.querySelector(s);
const projectSelect = $('#projectSelect');
const sidebar = $('#sidebar');
const content = $('#content');

let projects = {};
let currentProject = null;
let currentFile = null;

// ── Fetch data from our API ───────────────────────────────────
async function loadProjects() {
  const res = await fetch('/api/projects');
  projects = await res.json();
  const names = Object.keys(projects);

  projectSelect.innerHTML = '';
  if (names.length === 0) {
    projectSelect.innerHTML = '<option>No projects found</option>';
    return;
  }

  names.forEach(name => {
    const opt = document.createElement('option');
    opt.value = name;
    opt.textContent = name;
    projectSelect.appendChild(opt);
  });

  selectProject(names[0]);
}

function selectProject(name) {
  currentProject = name;
  const chapters = projects[name];
  sidebar.innerHTML = '<div class="section-label">Chapters</div>';

  chapters.forEach((ch, i) => {
    const a = document.createElement('a');
    a.dataset.file = ch.file;
    a.innerHTML = `<span class="ch-num">${ch.file === 'index.md' ? '⌂' : i}</span><span>${ch.title}</span>`;
    a.addEventListener('click', () => loadChapter(name, ch.file, a));
    sidebar.appendChild(a);
  });

  // Auto-load index
  const first = sidebar.querySelector('a');
  if (first) loadChapter(name, chapters[0].file, first);
}

async function loadChapter(project, file, linkEl) {
  // Track current chapter for re-render on theme switch
  currentFile = file;
  // Update active state
  sidebar.querySelectorAll('a').forEach(a => a.classList.remove('active'));
  if (linkEl) linkEl.classList.add('active');

  const res = await fetch(`/api/chapter?project=${encodeURIComponent(project)}&file=${encodeURIComponent(file)}`);
  const data = await res.json();

  // Configure marked with custom renderer for mermaid
  const renderer = new marked.Renderer();
  const defaultCodeRenderer = renderer.code;
  renderer.code = function({ text, lang }) {
    if (lang === 'mermaid') {
      // Sanitize: collapse stray newlines inside quoted node labels e.g. A0["Foo\n"]
      let clean = text.replace(/("(?:[^"\\]|\\.)*")/g, m => m.replace(/\n/g, ' ').replace(/\s+/g, ' '));
      // Also collapse newlines inside square bracket labels without quotes
      clean = clean.replace(/\[([^\]]*?)\n([^\]]*?)\]/g, '[$1 $2]');
      // Store raw source as data attribute for fallback on error
      const escaped = clean.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      return `<div class="mermaid-wrapper" data-raw="${btoa(unescape(encodeURIComponent(clean)))}"><pre class="mermaid">${clean}</pre></div>`;
    }
    return `<pre><code class="language-${lang || ''}">${text.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>`;
  };

  marked.setOptions({
    breaks: true,
    gfm: true,
    renderer: renderer,
  });

  let html = marked.parse(data.content);

  // Build prev/next nav
  const chapters = projects[project];
  const idx = chapters.findIndex(c => c.file === file);
  let nav = '<div class="chapter-nav">';
  if (idx > 0) {
    const prev = chapters[idx - 1];
    nav += `<a href="#" onclick="navTo('${prev.file}');return false"><div class="label">← Previous</div>${prev.title}</a>`;
  } else {
    nav += '<div></div>';
  }
  if (idx < chapters.length - 1) {
    const next = chapters[idx + 1];
    nav += `<a class="next" href="#" onclick="navTo('${next.file}');return false"><div class="label">Next →</div>${next.title}</a>`;
  }
  nav += '</div>';

  content.innerHTML = `<div class="md-body">${html}</div>${nav}`;
  content.scrollTop = 0;

  // Render mermaid diagrams individually — fallback to code block on error
  const mermaidEls = content.querySelectorAll('.md-body .mermaid-wrapper');
  for (const wrapper of mermaidEls) {
    const pre = wrapper.querySelector('.mermaid');
    try {
      await mermaid.run({ nodes: [pre] });
    } catch(e) {
      console.warn('Mermaid render failed, showing raw code:', e);
      const raw = decodeURIComponent(escape(atob(wrapper.dataset.raw)));
      wrapper.innerHTML = `<pre style="border-left:3px solid var(--amber);padding:16px;background:var(--code-bg);border-radius:var(--radius);overflow-x:auto;"><code style="color:var(--text-secondary);font-size:0.82rem;">${raw.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}</code></pre>`;
    }
  }
}

function navTo(file) {
  const links = sidebar.querySelectorAll('a');
  for (const a of links) {
    if (a.dataset.file === file) {
      loadChapter(currentProject, file, a);
      return;
    }
  }
}

projectSelect.addEventListener('change', () => selectProject(projectSelect.value));

// ── Theme Switching ───────────────────────────────────────────
const themeToggle = $('#themeToggle');

// Mermaid theme configs — use 'base' theme for full themeVariables control.
// Mermaid's built-in 'dark'/'default' themes override custom variables,
// causing contrast issues (e.g. black node fills in light mode).
// Every visual element needs explicit colors in 'base' theme since
// Mermaid derives missing values from primaryColor, which can produce
// unreadable dark-on-dark or light-on-light combinations.
const MERMAID_THEMES = {
  dark: {
    theme: 'base',
    themeVariables: {
      // Node styling
      primaryColor: '#2d3250',
      primaryTextColor: '#e2e4ed',
      primaryBorderColor: '#4f46e5',
      secondaryColor: '#1c1f2e',
      tertiaryColor: '#161822',
      mainBkg: '#2d3250',
      nodeBorder: '#4f46e5',
      nodeTextColor: '#e2e4ed',
      // Edge & label styling
      lineColor: '#818cf8',
      edgeLabelBackground: '#1c1f2e',
      labelTextColor: '#e2e4ed',
      labelBoxBkgColor: '#1c1f2e',
      labelBoxBorderColor: '#4f46e5',
      // Background & clusters
      background: '#161822',
      clusterBkg: '#1c1f2e',
      clusterBorder: '#2a2d3e',
      // Notes
      noteBkgColor: '#2d3250',
      noteTextColor: '#e2e4ed',
      noteBorderColor: '#4f46e5',
      // Typography
      fontFamily: 'Inter, sans-serif',
      fontSize: '14px'
    }
  },
  light: {
    theme: 'base',
    themeVariables: {
      // Node styling
      primaryColor: '#dde0f0',
      primaryTextColor: '#1a1c2e',
      primaryBorderColor: '#6366f1',
      secondaryColor: '#eef0f7',
      tertiaryColor: '#f8f9fc',
      mainBkg: '#dde0f0',
      nodeBorder: '#6366f1',
      nodeTextColor: '#1a1c2e',
      // Edge & label styling
      lineColor: '#6366f1',
      edgeLabelBackground: '#f8f9fc',
      labelTextColor: '#1a1c2e',
      labelBoxBkgColor: '#f8f9fc',
      labelBoxBorderColor: '#6366f1',
      // Background & clusters
      background: '#ffffff',
      clusterBkg: '#f0f1f5',
      clusterBorder: '#d5d7e2',
      // Notes
      noteBkgColor: '#eef0f7',
      noteTextColor: '#1a1c2e',
      noteBorderColor: '#6366f1',
      // Typography
      fontFamily: 'Inter, sans-serif',
      fontSize: '14px'
    }
  }
};

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('viewer-theme', theme);
  themeToggle.querySelectorAll('.toggle-option').forEach(opt => {
    opt.classList.toggle('active', opt.dataset.theme === theme);
  });
  // Re-initialize mermaid with theme-matched palette
  const mermaidCfg = MERMAID_THEMES[theme] || MERMAID_THEMES.dark;
  mermaid.initialize({ startOnLoad: false, ...mermaidCfg });
}

themeToggle.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  setTheme(current === 'dark' ? 'light' : 'dark');
  // Re-render current chapter so mermaid diagrams pick up the new palette
  if (currentProject && currentFile) {
    const activeLink = sidebar.querySelector('a.active');
    loadChapter(currentProject, currentFile, activeLink);
  }
});

// Apply saved theme on load (MUST run before loadProjects so mermaid
// is initialized with the correct palette before any diagrams render)
setTheme(localStorage.getItem('viewer-theme') || 'dark');

loadProjects();
</script>
</body>
</html>
"""

# ─── HTTP Handler ─────────────────────────────────────────────────────────────

class ViewerHandler(http.server.BaseHTTPRequestHandler):
    output_dir = OUTPUT_DIR

    def log_message(self, format, *args):
        # Quieter logging
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html, status=200):
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = dict(urllib.parse.parse_qsl(parsed.query))

        if path == "/":
            self.send_html(HTML_SHELL)

        elif path == "/api/projects":
            self.handle_projects()

        elif path == "/api/chapter":
            self.handle_chapter(params)

        else:
            self.send_response(404)
            self.end_headers()

    def handle_projects(self):
        """List all projects and their chapters."""
        result = {}
        out = Path(self.output_dir)
        if not out.exists():
            self.send_json(result)
            return

        for project_dir in sorted(out.iterdir()):
            if not project_dir.is_dir():
                continue
            chapters = []
            md_files = sorted(project_dir.glob("*.md"))
            # Put index.md first
            md_files.sort(key=lambda f: (0 if f.name == "index.md" else 1, f.name))
            for md_file in md_files:
                title = self._extract_title(md_file)
                chapters.append({"file": md_file.name, "title": title})
            if chapters:
                result[project_dir.name] = chapters

        self.send_json(result)

    def handle_chapter(self, params):
        """Return the markdown content of a chapter."""
        project = params.get("project", "")
        file = params.get("file", "")
        filepath = Path(self.output_dir) / project / file

        if not filepath.exists() or not filepath.is_file():
            self.send_json({"error": "Not found"}, 404)
            return

        content = filepath.read_text(encoding="utf-8")
        self.send_json({"content": content})

    @staticmethod
    def _extract_title(md_path):
        """Extract the first H1 heading from a markdown file, or fall back to filename."""
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("# "):
                        return line[2:].strip()
        except Exception:
            pass
        # Fallback: clean up filename
        name = md_path.stem
        name = re.sub(r"^\d+_", "", name)  # remove leading number
        return name.replace("_", " ").title()


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_server(port=8000, output_dir="output"):
    ViewerHandler.output_dir = output_dir
    server = http.server.HTTPServer(("localhost", port), ViewerHandler)
    url = f"http://localhost:{port}"
    print(f"✦ Tutorial Viewer running at {url}")
    print(f"  Serving tutorials from: {os.path.abspath(output_dir)}/")
    print(f"  Press Ctrl+C to stop.\n")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Serve generated tutorials in a local web viewer.")
    parser.add_argument("-p", "--port", type=int, default=8000, help="Port to serve on (default: 8000)")
    parser.add_argument("-d", "--dir", default="output", help="Output directory to serve (default: output)")
    args = parser.parse_args()
    run_server(port=args.port, output_dir=args.dir)
