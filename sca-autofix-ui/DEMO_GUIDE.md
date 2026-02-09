# SCA Fix Advisor - Judge Demo Guide

## Quick Reference Card

**Demo Duration:** 60 seconds  
**Target Audience:** Security analysts, DevSecOps teams  
**Problem Solved:** Too many vulnerable repos, unclear upgrade paths, risky code changes  
**Solution:** AI-powered prioritization + decision rationale + automated patch generation

---

## The 60-Second Pitch

### Opening Hook (5s)
*"Let me show you how we help security teams fix 10 critical vulnerabilities in under a minute."*

### Screen 1: Security Posture Dashboard (10s)

**What Judges See:**
```
┌─────────────────────────────────────────────────────────────┐
│  🔒 SCA Fix Advisor                                         │
│  Enterprise Security Posture Dashboard                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Security Overview                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐│
│  │ 🚨 Exploitable  │  │ 📊 Total        │  │ ✅ Ready    ││
│  │    10           │  │    8            │  │    8        ││
│  │ Requires action │  │ Vulnerable Repos│  │ to Fix      ││
│  └─────────────────┘  └─────────────────┘  └─────────────┘│
│                                                             │
│  Recommended Action                                         │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  🎯 Fix Highest-Impact Risk                          │ │
│  │  Will review: payment-gateway-api (P1)               │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Vulnerable Repository Queue (8 repositories)               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ payment-gateway-api     [P1] 🔴 1 libs  [Review]    │  │
│  │ frontend-dashboard      [P1] 🔴 1 libs  [Review]    │  │
│  │ audit-logging-service   [P1] 🔴 1 libs  [Review]    │  │
│  │ config-manager          [P2] 🔴 1 libs  [Review]    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Talking Points:**
- "Dashboard shows 10 critical repos, 8 ready for immediate fix"
- "Our AI agent has already analyzed upgrade paths"
- "One click to fix highest priority issue"

---

### Screen 2: Repository Detail - Decision Rationale (25s)

**What Judges See:**
```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Queue                                            │
│                                                             │
│  ╔═══════════════════════════════════════════════════════╗ │
│  ║  payment-gateway-api                                  ║ │
│  ║  [P1] | 📍 github.com/company/payment-gateway-api   ║ │
│  ║  🕐 Last detected: 2026-01-27 14:23                 ║ │
│  ╚═══════════════════════════════════════════════════════╝ │
│                                                             │
│  🔴 What's Vulnerable                                       │
│  ┌─────────────┐                                           │
│  │  requests   │                                           │
│  │  Current:   │                                           │
│  │  2.6.0      │                                           │
│  └─────────────┘                                           │
│                                                             │
│  📦 Available Upgrade Options                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                  │
│  │ ✅ 2.31.0│ │   2.28.0 │ │   2.27.1 │                  │
│  │(Recommend)│ │          │ │          │                  │
│  └──────────┘ └──────────┘ └──────────┘                  │
│                                                             │
│  📊 Decision Rationale: Version Comparison                  │
│  Analysis of upgrade impact for each candidate version      │
│                                                             │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃ ✅ 2.31.0   Files: 2   Call Sites: 5              ┃  │
│  ┃           Confidence: 95% ████████████████░░       ┃  │
│  ┃           Notes: Minimal breaking changes.          ┃  │
│  ┃           Recommended. Adds timeout parameter.      ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                             │
│     2.28.0     Files: 2   Call Sites: 5                   │
│                Confidence: 88% █████████████░░░            │
│                Notes: Stable release. Minor API changes.   │
│  ───────────────────────────────────────────────────────   │
│     2.27.1     Files: 3   Call Sites: 8                   │
│                Confidence: 75% ██████████░░░░░             │
│                Notes: Breaking changes in proxy handling.  │
│  ───────────────────────────────────────────────────────   │
└─────────────────────────────────────────────────────────────┘
```

**Talking Points:**
- "AI agent analyzed 3 possible upgrades"
- "Recommended version: **2.31.0** - only 2 files, 5 call sites, 95% confidence"
- "Clear reasoning: minimal breaking changes, adds timeout support"
- "**Decision-first approach** - rationale BEFORE code"

---

### Screen 3: Split-Screen Code Review (15s)

**What Judges See:**
```
┌─────────────────────────────────────────────────────────────┐
│  💻 Code Review: Proposed Changes                           │
│                                                             │
│  📁 Impacted Files (2)  ▼                                   │
│                                                             │
│  ┌─────────────────────────┬─────────────────────────────┐ │
│  │ 🔴 Current Vulnerable   │ ✅ Suggested Fix            │ │
│  │         Code            │                             │ │
│  ├─────────────────────────┼─────────────────────────────┤ │
│  │ 1  import requests      │ 1  import requests          │ │
│  │ 2  from flask import... │ 2  from flask import...     │ │
│  │ 3                       │ 3                           │ │
│  │ 4  @app.route('/fetch') │ 4  @app.route('/fetch')     │ │
│  │ 5  def fetch_data():    │ 5  def fetch_data():        │ │
│  │ 6    url = request...   │ 6    url = request...       │ │
│  │ 7    # Vulnerable:      │ 7    # Fixed:               │ │
│  │ 8    response = req...  │ 8    response = req...      │ │
│  │ 9      verify=False ❌  │ 9      verify=True  ✅      │ │
│  │10                       │10      timeout=30  ✅       │ │
│  │11    return json...     │11    return json...         │ │
│  └─────────────────────────┴─────────────────────────────┘ │
│                                                             │
│  📋 View Unified Diff  ▼                                    │
│                                                             │
│  🎯 Review Decision                                         │
│  ┌────────────────────────┐ ┌────────────────────────────┐│
│  │ ✅ Approve and Export  │ │ ❌ Reject                  ││
│  │    Patch               │ │                            ││
│  └────────────────────────┘ └────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Talking Points:**
- "Side-by-side diff shows the fix: verify=False → verify=True"
- "Syntax highlighted, clear visual difference"
- "Two impacted files, simple changes"
- "Ready to approve and export as git patch"

---

### Screen 4: Patch Export (5s)

**What Judges See:**
```
┌─────────────────────────────────────────────────────────────┐
│  ✅ Patch approved! Download the diff file to apply changes.│
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  📥 Download .diff File                               │  │
│  │  payment-gateway-api_fix.diff                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Patch Contents:                                            │
│  # SCA Fix Advisor - Patch Export                          │
│  # Repository: payment-gateway-api                          │
│  # Vulnerability: requests 2.6.0 → 2.31.0                  │
│  # Generated: 2026-01-28 15:30:45                          │
│  # Files impacted: 2                                        │
│  #   - src/api/endpoints.py                                │
│  #   - src/utils/http_client.py                            │
│                                                             │
│  --- a/src/api/endpoints.py                                │
│  +++ b/src/api/endpoints.py                                │
│  @@ -8,7 +8,8 @@                                           │
│   def fetch_data():                                         │
│       url = request.json.get('url')                        │
│  -    response = requests.get(url, verify=False)           │
│  +    response = requests.get(url, verify=True, timeout=30)│
│       return jsonify(response.json())                      │
└─────────────────────────────────────────────────────────────┘
```

**Talking Points:**
- "One click: patch file downloaded"
- "Ready to apply with `git apply`"
- "Includes metadata: repo, vulnerability, files changed"
- "Analyst can review and merge immediately"

---

### Screen 5: Back to Dashboard (5s)

**What Judges See:**
```
┌─────────────────────────────────────────────────────────────┐
│  🔒 SCA Fix Advisor                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐│
│  │ 🚨 Exploitable  │  │ 📊 Total        │  │ ✅ Ready    ││
│  │    9  ⬇️ -1     │  │    7            │  │    7        ││
│  └─────────────────┘  └─────────────────┘  └─────────────┘│
│                                                             │
│  Filter: [P1] [P2]  Search: [frontend     ]                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ frontend-dashboard      [P1] 🔴 1 libs  [Review]    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Talking Points:**
- "One down, next! KPI updated automatically"
- "Filter and search to find specific repos"
- "Repeat process for remaining vulnerabilities"
- "**10 repos fixed in 10 minutes** instead of hours"

---

## Key Features to Highlight

### 1. Decision-First Design ⭐
- Rationale shown **BEFORE** code
- Judges see **why** before **what**
- Risk assessment upfront

### 2. Enterprise-Grade UX ⭐
- Clean, professional styling
- Priority badges (P1/P2/P3) with color coding
- Confidence scores with visual indicators
- No clutter, decision-focused

### 3. AI Agent Integration (Mocked) ⭐
- Clear TODO markers for production
- Realistic mock outputs
- 8 scenarios covering Python, JS, Java
- Real CVEs: Log4Shell, prototype pollution, SSRF

### 4. Complete Workflow ⭐
- Discover → Prioritize → Analyze → Review → Approve/Reject
- End-to-end in < 60 seconds
- Exportable patch files

### 5. Data-Driven ⭐
- Unity Catalog integration (planned)
- Multiple upgrade candidates
- Quantified impact (files, call sites)
- Confidence scoring

---

## Technical Highlights for Judges

### Architecture
- **Frontend:** Streamlit (rapid prototyping)
- **Data Source:** Unity Catalog (Delta tables)
- **Agent:** UC Functions (future integration)
- **Mock:** 8 realistic scenarios with code diffs

### Code Quality
- Modular functions (render_home, render_detail, generate_patch)
- Type hints throughout
- Session state navigation
- Error handling for missing UC connection

### Scalability
- Filterable/searchable table (scales to 100+ repos)
- Lazy loading (only detail page loads agent output)
- Diff generation in < 100ms
- In-memory for demo, database-backed for production

---

## Potential Judge Questions & Answers

**Q: Is the agent real?**  
A: "No, mocked for the prototype. Clear TODO markers show where we'll integrate UC Functions. The data contract is production-ready."

**Q: How do you prevent false positives?**  
A: "Confidence scoring + human-in-the-loop. Analyst reviews the diff before approving. Reject option captures feedback."

**Q: What about breaking changes?**  
A: "Agent analyzes multiple candidate versions. Shows estimated impact (files, call sites) and flags breaking changes in notes."

**Q: How does prioritization work?**  
A: "P1 = exploitable CVEs, P2 = high severity, P3 = medium. Sort by priority + detection time. CTA auto-selects highest risk."

**Q: Can I bulk approve?**  
A: "Not in v1. Design choice: each fix needs review. Future: batch mode for low-risk upgrades."

**Q: What languages are supported?**  
A: "Demo shows Python, JavaScript, Java. Agent can analyze any language - just needs AST parsing."

---

## What Judges Will Love

✅ **Speed:** 60-second demo, instant navigation  
✅ **Polish:** Enterprise styling, no rough edges  
✅ **Clarity:** Decision rationale front and center  
✅ **Realism:** Actual CVEs, real code samples  
✅ **Completeness:** Full workflow from discovery to patch  
✅ **Extensibility:** Clear path to production integration  

---

## What Sets This Apart

1. **Decision-first, not code-first** - Other tools dump diffs; we explain the "why"
2. **Multi-candidate analysis** - Compare 2-3 upgrade paths with pros/cons
3. **Confidence scoring** - Quantify risk of each upgrade
4. **Human-in-the-loop** - Analyst approves/rejects with feedback
5. **Patch export** - Git-ready diff file, not just suggestions

---

## Closing Statement

*"We've turned a multi-day process into 60 seconds per repo. Security teams can now review and fix vulnerabilities 10x faster with confidence. The AI does the analysis; the human makes the decision. That's the future of DevSecOps."*

---

**Total Demo Time:** 60 seconds  
**Repos Fixed:** 1 (with clear path to fix all 8)  
**Judge Wow Factor:** 🚀🚀🚀


