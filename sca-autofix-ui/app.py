"""
SCA Vulnerabilities Scanning - Streamlit App
Simple, clean, production-ready
"""

import streamlit as st
import pandas as pd
import os
import time
import json
import requests
from datetime import datetime
from difflib import unified_diff
from demo_fixtures import get_mock_repos, get_mock_agent_analysis

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load config from environment
DATA_MODE = os.getenv("DATA_MODE", "mock")
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT", "fix_advisor_agent_endpoint")
WORKSPACE_HOST = os.getenv("WORKSPACE_HOST", "")


# ============================================================================
# AGENT CLIENT
# ============================================================================


def call_agent_endpoint(
    repo_path: str,
    repo_url: str,
    library: str,
    current_version: str,
    target_version: str,
    cve_ids: list = None,
) -> dict:
    """
    Call the SCA AutoFix agent endpoint for real analysis.

    Args:
        repo_path: Path to the repository
        repo_url: Git URL of the repository
        library: Library name (e.g., jackson-databind)
        current_version: Current vulnerable version
        target_version: Target safe version
        cve_ids: List of CVE identifiers

    Returns:
        Analysis result dict with files_impacted, lines_changed, file_diffs, generated_ts
    """
    try:
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

        w = WorkspaceClient()

        # Build the analysis prompt
        cve_str = ", ".join(cve_ids) if cve_ids else "N/A"
        prompt = f"""Analyze the following vulnerability upgrade and generate code fixes:

Repository: {repo_path}
Git URL: {repo_url}
Library: {library}
Current Version: {current_version} (vulnerable)
Target Version: {target_version} (safe)
CVEs: {cve_str}

Please:
1. Clone the repository and find usages of {library}
2. Get the API diff between {current_version} and {target_version}
3. Match breaking changes with code usages
4. Generate code fixes for each affected file

Return the analysis with specific file changes."""

        # Call the agent endpoint
        response = w.serving_endpoints.query(
            name=AGENT_ENDPOINT,
            messages=[ChatMessage(role=ChatMessageRole.USER, content=prompt)],
            max_tokens=4096,
        )

        # Parse the agent response
        agent_output = response.choices[0].message.content if response.choices else ""

        # Try to extract structured data from response
        # The agent may return JSON or structured text
        result = parse_agent_response(
            agent_output, repo_path, library, current_version, target_version
        )
        return result

    except ImportError:
        st.error("❌ Databricks SDK not available. Cannot call agent endpoint.")
        return get_mock_agent_analysis(
            repo_path, library, current_version, target_version
        )
    except Exception as e:
        st.error(f"❌ Agent call failed: {e}")
        st.warning("Falling back to mock data...")
        return get_mock_agent_analysis(
            repo_path, library, current_version, target_version
        )


def parse_agent_response(
    agent_output: str,
    repo_path: str,
    library: str,
    current_version: str,
    target_version: str,
) -> dict:
    """
    Parse agent response into structured analysis result.

    The agent may return:
    1. JSON with structured data
    2. Markdown with code blocks
    3. Plain text with file changes
    """
    result = {
        "files_impacted": 0,
        "lines_changed": 0,
        "file_diffs": {},
        "generated_ts": datetime.now(),
        "agent_response": agent_output,  # Keep raw response
    }

    # Try to extract JSON from response
    try:
        # Look for JSON blocks in the response
        if "```json" in agent_output:
            json_start = agent_output.find("```json") + 7
            json_end = agent_output.find("```", json_start)
            json_str = agent_output[json_start:json_end].strip()
            data = json.loads(json_str)

            if "files_impacted" in data:
                result["files_impacted"] = data["files_impacted"]
            if "lines_changed" in data:
                result["lines_changed"] = data["lines_changed"]
            if "file_diffs" in data:
                result["file_diffs"] = data["file_diffs"]
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to extract code blocks for file diffs
    try:
        import re

        # Pattern: ```language:filepath or ```filepath
        code_blocks = re.findall(
            r"```(?:java|python|xml)?:?([^\n`]+)?\n(.*?)```", agent_output, re.DOTALL
        )

        file_diffs = {}
        for filepath, code in code_blocks:
            if filepath and filepath.strip():
                filepath = filepath.strip()
                if filepath not in file_diffs:
                    file_diffs[filepath] = {"old_code": "", "new_code": code.strip()}
                else:
                    file_diffs[filepath]["new_code"] = code.strip()

        if file_diffs:
            result["files_impacted"] = len(file_diffs)
            result["file_diffs"] = file_diffs
            # Estimate lines changed
            total_lines = sum(
                len(d.get("new_code", "").split("\n")) for d in file_diffs.values()
            )
            result["lines_changed"] = total_lines
    except Exception:
        pass

    # If no structured data found, create a summary file
    if not result["file_diffs"]:
        result["file_diffs"] = {
            "AGENT_ANALYSIS.md": {
                "old_code": f"# Analysis pending for {library}",
                "new_code": f"# Agent Analysis: {library} {current_version} → {target_version}\n\n{agent_output}",
            }
        }
        result["files_impacted"] = 1
        result["lines_changed"] = len(agent_output.split("\n"))

    return result


def get_analysis(
    repo_path: str,
    repo_url: str,
    library: str,
    current_version: str,
    target_version: str,
    cve_ids: list = None,
) -> dict:
    """
    Get analysis - uses mock or real agent based on DATA_MODE.
    """
    if DATA_MODE == "production":
        return call_agent_endpoint(
            repo_path, repo_url, library, current_version, target_version, cve_ids
        )
    else:
        return get_mock_agent_analysis(
            repo_path, library, current_version, target_version
        )


st.set_page_config(
    page_title="SCA Vulnerabilities Scanning",
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# CSS Styling
st.markdown(
    """
<style>
    .main .block-container { padding-top: 2rem; max-width: 100%; }
    .priority-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 12px; font-weight: 600; font-size: 0.875rem; }
    .priority-critical { background-color: #fee; color: #c00; border: 1px solid #fcc; }
    .priority-high { background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
    .priority-medium { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .priority-low { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
    .priority-informational { background-color: #e2e3e5; color: #383d41; border: 1px solid #d6d8db; }
    .repo-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 8px; margin-bottom: 2rem; margin-top: 1.5rem; }
    .vuln-badge { display: inline-block; padding: 0.25rem 0.6rem; border-radius: 8px; font-weight: 600; font-size: 0.8rem; margin-left: 0.5rem; }
    .vuln-zero { background-color: #c6f6d5; color: #22543d; }
    .vuln-low { background-color: #fef5e7; color: #6b4423; }
    .vuln-high { background-color: #fed7d7; color: #742a2a; }
</style>
""",
    unsafe_allow_html=True,
)

# Session State Init
for key, default in {
    "current_page": "home",
    "selected_repo_path": None,
    "selected_library": None,
    "analysis_cache": {},
    "selected_version_for_analysis": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def badge(priority: str) -> str:
    """Priority badge HTML."""
    return f'<span class="priority-badge priority-{priority.lower()}">{priority.upper()}</span>'


def vuln_badge(count: int) -> str:
    """Vulnerability count badge HTML."""
    cls, text = (
        ("vuln-zero", "✓ 0 vulns")
        if count == 0
        else ("vuln-low", f"⚠ {count} vulns")
        if count <= 2
        else ("vuln-high", f"🔴 {count} vulns")
    )
    return f'<span class="vuln-badge {cls}">{text}</span>'


def diff(old: str, new: str, file: str) -> str:
    """Generate unified diff."""
    return "".join(
        unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{file}",
            tofile=f"b/{file}",
            lineterm="\n",
        )
    )


def load_data() -> pd.DataFrame:
    """Load vulnerable libraries from UC or mock."""
    if os.getenv("DATA_MODE") == "production":
        try:
            from pyspark.sql import SparkSession
            import json

            spark = SparkSession.builder.getOrCreate()
            catalog = os.getenv("UC_CATALOG")
            schema = os.getenv("UC_SCHEMA")
            table = os.getenv("UC_TABLE")
            full_table = f"{catalog}.{schema}.{table}"

            df = spark.sql(f"""
                SELECT * FROM {full_table}
                WHERE status IN ('ready', 'analyzing')
                ORDER BY CASE priority 
                    WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 
                    WHEN 'Low' THEN 4 ELSE 5 
                END, last_detected_ts DESC
                LIMIT 100
            """).toPandas()

            # Parse JSON columns from UC (stored as strings)
            if "cve_ids" in df.columns and len(df) > 0:
                df["cve_ids"] = df["cve_ids"].apply(
                    lambda x: json.loads(x) if isinstance(x, str) else x
                )
            if "candidate_versions" in df.columns and len(df) > 0:
                df["candidate_versions"] = df["candidate_versions"].apply(
                    lambda x: json.loads(x) if isinstance(x, str) else x
                )
                # Parse nested dates in candidate_versions
                for idx, row in df.iterrows():
                    if isinstance(row["candidate_versions"], list):
                        for cv in row["candidate_versions"]:
                            if isinstance(cv.get("release_date"), str):
                                cv["release_date"] = pd.to_datetime(cv["release_date"])
                            if "detected_ts" not in cv:
                                cv["detected_ts"] = row.get(
                                    "last_detected_ts", datetime.now()
                                )

            # Convert timestamp columns
            if "last_detected_ts" in df.columns:
                df["last_detected_ts"] = pd.to_datetime(df["last_detected_ts"])

            return df
        except Exception as e:
            st.error(f"❌ Unity Catalog Error: {e}")
            st.warning("Falling back to mock data...")
    return get_mock_repos()


def nav(page: str, repo_path: str = None, library: str = None):
    """Navigate between pages."""
    st.session_state.current_page = page
    st.session_state.selected_repo_path = repo_path
    st.session_state.selected_library = library
    st.rerun()


# ============================================================================
# HOME VIEW
# ============================================================================


def home():
    """Home dashboard."""
    # Mode indicator in sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        mode_color = "#28a745" if DATA_MODE == "production" else "#6c757d"
        mode_icon = "🔵" if DATA_MODE == "production" else "⚪"
        st.markdown(
            f'{mode_icon} **Mode:** <span style="color: {mode_color}; font-weight: bold;">'
            f"{DATA_MODE.upper()}</span>",
            unsafe_allow_html=True,
        )
        if DATA_MODE == "production":
            st.caption(f"Agent: `{AGENT_ENDPOINT}`")
        else:
            st.caption("Using demo fixtures")
        st.markdown("---")

    # Header
    if os.path.exists("ing_logo.png"):
        st.markdown(
            f'<div style="display: flex; align-items: center; gap: 30px;"><img src="data:image/png;base64,{__import__("base64").b64encode(open("ing_logo.png", "rb").read()).decode()}" style="height: 60px;"><div><h1 style="margin: 0;">SCA Vulnerabilities Scanning</h1><p style="margin: 0; font-weight: 600; color: #666;">Enterprise Security Dashboard</p></div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.title("🦁 SCA Vulnerabilities Scanning")
    st.markdown("---")

    # Load data
    df = load_data()
    if df.empty:
        st.warning("No vulnerable libraries found.")
        return

    # KPIs
    st.subheader("Security Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric(
        "🔴 Critical", len(df[df["priority"] == "Critical"]), delta="Immediate action"
    )
    col2.metric("🟠 High", len(df[df["priority"] == "High"]))
    col3.metric("📚 Total", len(df))
    st.markdown("---")

    # Filters
    st.subheader("Vulnerable Libraries")
    col1, col2 = st.columns([1, 2])
    priority_filter = col1.multiselect(
        "Priority",
        ["Critical", "High", "Medium", "Low", "Informational"],
        ["Critical", "High", "Medium"],
    )
    search = col2.text_input("Search", "")

    # Apply filters
    filtered = df[df["priority"].isin(priority_filter)]
    if search:
        filtered = filtered[
            filtered["repo_name"].str.contains(search, case=False, na=False)
            | filtered["library"].str.contains(search, case=False, na=False)
        ]

    if filtered.empty:
        st.info("No libraries match filters.")
        return

    st.markdown(f"**{len(filtered)} libraries**")

    # Display list
    for idx, row in filtered.iterrows():
        col1, col2, col3, col4, col5, col6 = st.columns([2.5, 2, 1, 1.5, 2, 1])
        col1.markdown(f"**{row['repo_name']}**")
        col1.caption(f"`{row['repo_path']}`")
        col2.markdown(f"🔴 **{row['library']}** `{row['current_version']}`")
        col3.markdown(badge(row["priority"]), unsafe_allow_html=True)
        col4.markdown(f"📦 {len(row['candidate_versions'])} versions")
        col5.markdown(f"🕐 {row['last_detected_ts'].strftime('%Y-%m-%d %H:%M')}")
        if col6.button("Review", key=f"r_{idx}", use_container_width=True):
            nav("detail", row["repo_path"], row["library"])
        st.markdown("---")


# ============================================================================
# DETAIL VIEW
# ============================================================================


def detail():
    """Library detail view."""
    df = load_data()
    row = df[
        (df["repo_path"] == st.session_state.selected_repo_path)
        & (df["library"] == st.session_state.selected_library)
    ]

    if row.empty:
        st.error("Library not found")
        if st.button("← Back"):
            nav("home")
        return

    row = row.iloc[0]

    # Back button
    if st.button("← Back"):
        nav("home")

    # Header
    st.markdown(
        f'<div class="repo-header"><h1>{row["repo_name"]} / {row["library"]}</h1><p style="margin: 0.5rem 0 0 0;">{badge(row["priority"])}&nbsp;|&nbsp; Current: <strong>{row["current_version"]}</strong>&nbsp;|&nbsp; <a href="{row["repo_url"]}" target="_blank" style="color: white;">{row["repo_path"]}</a></p></div>',
        unsafe_allow_html=True,
    )

    # Vulnerability Info
    st.subheader("🔴 Vulnerability Details")
    col1, col2 = st.columns(2)
    col1.markdown(
        f"**Library:** `{row['library']}`\n\n**Current Version:** `{row['current_version']}`\n\n**CVSS Score:** {row.get('cvss_score', 'N/A')}"
    )
    if row.get("cve_ids"):
        col2.markdown(f"**CVEs:** {', '.join(row['cve_ids'])}")
    st.markdown("---")

    # Version List
    st.subheader("📦 Available Upgrade Versions")
    col_info, col_detect = st.columns([3, 1])
    col_info.markdown(
        "*Click Analyze to check upgrade impact. Versions with fewer vulnerabilities are safer.*"
    )
    col_detect.markdown(
        f"**Last Detected:** {row['last_detected_ts'].strftime('%Y-%m-%d %H:%M')}"
    )

    cache_key = f"{row['repo_path']}_{row['library']}"

    # Sort candidate versions by detected_ts descending (latest first)
    sorted_versions = sorted(
        row["candidate_versions"],
        key=lambda x: x.get("detected_ts", datetime.min),
        reverse=True,
    )

    for v_info in sorted_versions:
        version, vuln_count = v_info["version"], v_info["vulnerability_count"]
        release_date = v_info.get("release_date")
        detected_ts = v_info.get("detected_ts")
        analysis_key = f"{cache_key}_{version}"
        analyzed = analysis_key in st.session_state.analysis_cache

        col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 1.5, 3, 1.5])
        col1.markdown(f"**`{version}`**")
        col2.markdown(vuln_badge(vuln_count), unsafe_allow_html=True)
        if release_date:
            col3.markdown(f"🕐 {release_date.strftime('%Y-%m-%d')}")
        if analyzed:
            a = st.session_state.analysis_cache[analysis_key]
            col4.markdown(
                f"✅ **Analyzed:** {a['files_impacted']} files, {a['lines_changed']} lines"
            )

        # Show Analyze button or View Results button
        if not analyzed:
            if col5.button(
                "🔍 Analyze", key=f"a_{analysis_key}", use_container_width=True
            ):
                status = st.empty()
                prog = st.progress(0)

                if DATA_MODE == "production":
                    # Production mode: call real agent with streaming progress
                    status.markdown("🤖 **Calling SCA AutoFix Agent...**")
                    prog.progress(20)

                    # Get CVE IDs from row
                    cve_ids = row.get("cve_ids", [])
                    if isinstance(cve_ids, str):
                        try:
                            cve_ids = json.loads(cve_ids)
                        except:
                            cve_ids = [cve_ids] if cve_ids else []

                    status.markdown("🤖 **Agent analyzing repository...**")
                    prog.progress(50)

                    # Call the real agent
                    analysis_result = get_analysis(
                        repo_path=row["repo_path"],
                        repo_url=row.get("repo_url", ""),
                        library=row["library"],
                        current_version=row["current_version"],
                        target_version=version,
                        cve_ids=cve_ids,
                    )

                    st.session_state.analysis_cache[analysis_key] = analysis_result
                else:
                    # Mock mode: simulate progress with delays
                    steps = [
                        (20, "✅ Cloning repository...", 0.8),
                        (
                            40,
                            "✅ Repository cloned\n\n🔄 Analyzing code patterns...",
                            1.0,
                        ),
                        (
                            60,
                            "✅ Code patterns analyzed\n\n🔄 Checking compatibility...",
                            0.9,
                        ),
                        (
                            80,
                            "✅ Compatibility checked\n\n🔄 Generating patches...",
                            0.7,
                        ),
                    ]

                    for pct, msg, delay in steps:
                        status.markdown(f"🤖 **Agent analyzing...**\n\n{msg}")
                        prog.progress(pct)
                        time.sleep(delay)

                    st.session_state.analysis_cache[analysis_key] = (
                        get_mock_agent_analysis(
                            row["repo_path"],
                            row["library"],
                            row["current_version"],
                            version,
                        )
                    )

                st.session_state.selected_version_for_analysis = version
                prog.progress(100)
                status.success("✅ Analysis complete!")
                time.sleep(0.5)
                st.rerun()
        else:
            # Show "View Results" button for already analyzed versions
            if col5.button(
                "📊 View Results",
                key=f"view_{analysis_key}",
                use_container_width=True,
                type="primary",
            ):
                st.session_state.selected_version_for_analysis = version
                st.rerun()

    # Analysis Results
    if st.session_state.selected_version_for_analysis:
        v = st.session_state.selected_version_for_analysis
        ak = f"{cache_key}_{v}"

        if ak in st.session_state.analysis_cache:
            a = st.session_state.analysis_cache[ak]

            st.markdown("---")
            st.subheader(
                f"🤖 Code Changes: {row['library']} {row['current_version']} → {v}"
            )

            # Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Files", a["files_impacted"])
            col2.metric("Lines", a["lines_changed"])
            col3.metric("Time", a["generated_ts"].strftime("%H:%M:%S"))
            st.markdown("---")

            # File diff
            files = a["file_diffs"]
            sel_file = st.selectbox("Select file:", list(files.keys()), key=f"fs_{ak}")

            if sel_file:
                fd = files[sel_file]
                col_l, col_r = st.columns(2)
                lang = (
                    "python"
                    if sel_file.endswith(".py")
                    else "javascript"
                    if sel_file.endswith(".js")
                    else "text"
                )
                col_l.markdown(f"##### 🔴 Before ({row['current_version']})")
                col_l.code(fd["old_code"], language=lang, line_numbers=True)
                col_r.markdown(f"##### ✅ After ({v})")
                col_r.code(fd["new_code"], language=lang, line_numbers=True)

                with st.expander("📋 Unified Diff"):
                    st.code(
                        diff(fd["old_code"], fd["new_code"], sel_file), language="diff"
                    )

            st.markdown("---")

            # Actions
            st.subheader("🎯 Decision")
            col1, col2, _ = st.columns([1, 1, 2])

            if col1.button(
                "✅ Approve & Export",
                type="primary",
                use_container_width=True,
                key=f"ap_{ak}",
            ):
                patches = [
                    diff(files[f]["old_code"], files[f]["new_code"], f) for f in files
                ]
                patch = f"""# SCA Vulnerabilities Scanning - Patch Export
# Repository: {row["repo_name"]} ({row["repo_path"]})
# Library: {row["library"]} {row["current_version"]} → {v}
# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
# Files: {a["files_impacted"]} | Lines: {a["lines_changed"]}

{chr(10).join(patches)}
"""
                st.download_button(
                    "📥 Download",
                    patch,
                    f"{row['library']}_{v}.patch",
                    "text/plain",
                    use_container_width=True,
                    key=f"dl_{ak}",
                )
                st.success("✅ Approved!")

            with col2.popover("❌ Reject", use_container_width=True):
                reason = st.text_area("Reason:", key=f"rr_{ak}")
                if st.button(
                    "Submit", type="secondary", use_container_width=True, key=f"rs_{ak}"
                ):
                    if reason.strip():
                        st.warning(f"❌ Rejected: {reason}")
                        st.session_state.selected_version_for_analysis = None
                        st.rerun()
                    else:
                        st.error("Provide reason")


# ============================================================================

if st.session_state.current_page == "home":
    home()
elif st.session_state.current_page == "detail":
    detail()
