"""
MCP tools for vulnerability scanning and dependency analysis.

This module defines all the tools that the MCP server exposes to AI agents
and other clients. Each tool performs a specific function related to
scanning repositories for security vulnerabilities and managing patches.
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from server import utils

logger = logging.getLogger(__name__)
from services import (
    CodeAnalyzer,
    DiffGenerator,
    DatabricksGitClient,
    PackageRegistryClient,
    VulnerabilityScanner,
)

# UCIntegration imported lazily to avoid pyspark dependency at startup
# from services.uc_integration import UCIntegration
from models import (
    UpgradePlan,
    UpgradeRecommendation,
    VulnerabilitySeverity,
)


def load_tools(mcp_server):
    """
    Register all MCP tools with the server.

    This function is called during server initialization to register all
    available vulnerability scanning tools with the MCP server instance.

    Args:
        mcp_server: The FastMCP server instance to register tools with
    """

    @mcp_server.tool
    def scan_repo_dependencies(repo_path: str, branch: str = "main") -> dict:
        """
        Scan a Databricks Repo to extract all library dependencies.

        This tool analyzes manifest files (requirements.txt, package.json, pom.xml, etc.)
        in the repository to identify which packages and versions are being used.

        Supports multiple ecosystems:
        - Python: requirements.txt, pyproject.toml, setup.py
        - JavaScript/Node.js: package.json
        - Java/Maven: pom.xml
        - R: DESCRIPTION

        Args:
            repo_path: Path to Databricks Repo (e.g., /Repos/user@company.com/my-repo)
            branch: Git branch to scan (default: "main")

        Returns:
            dict: {
                "repo_path": str,
                "branch": str,
                "packages": {
                    "python": {"requests": "2.28.0", "pandas": "1.5.3"},
                    "javascript": {"react": "18.2.0"},
                    ...
                },
                "manifest_files": ["requirements.txt", "package.json"],
                "total_packages": 15
            }

        Example:
            scan_repo_dependencies(
                repo_path="/Repos/john.doe@company.com/my-project",
                branch="main"
            )
        """
        try:
            # Get workspace client (use app-level auth like diagnostic tool)
            w = utils.get_workspace_client()

            # Create code analyzer
            analyzer = CodeAnalyzer(w)

            # Scan the repository
            dependency_info = analyzer.scan_repository(repo_path, branch)

            return dependency_info.model_dump()

        except Exception as e:
            return {
                "error": str(e),
                "message": f"Failed to scan repository: {repo_path}",
            }

    @mcp_server.tool
    def check_vulnerabilities(
        dependencies: dict,
        severity_threshold: str = "medium",
    ) -> dict:
        """
        Check dependencies against vulnerability databases.

        This tool queries the OSV.dev vulnerability database (which aggregates
        multiple sources including NVD, GitHub Security Advisory, etc.) to find
        known security vulnerabilities in the specified packages.

        No downloads required - uses API-based lookups for instant results.

        Args:
            dependencies: Dict of {ecosystem: {package: version}}
                         e.g., {"python": {"requests": "2.28.0"}}
            severity_threshold: Minimum severity to report
                              Options: "low", "medium", "high", "critical"
                              Default: "medium"

        Returns:
            dict: {
                "repo_path": str,
                "scan_timestamp": str (ISO format),
                "total_packages": int,
                "vulnerable_packages_count": int,
                "vulnerable_packages": [
                    {
                        "name": "requests",
                        "ecosystem": "python",
                        "current_version": "2.28.0",
                        "recommended_version": "2.31.0",
                        "vulnerabilities": [
                            {
                                "cve_id": "CVE-2023-32681",
                                "severity": "high",
                                "cvss_score": 7.5,
                                "description": "...",
                                "fixed_versions": [">= 2.31.0"]
                            }
                        ]
                    }
                ],
                "severity_breakdown": {
                    "critical": 2,
                    "high": 5,
                    "medium": 3,
                    "low": 1
                }
            }

        Example:
            check_vulnerabilities(
                dependencies={"python": {"requests": "2.28.0"}},
                severity_threshold="high"
            )
        """
        try:
            # Run async vulnerability scan
            async def scan():
                async with VulnerabilityScanner() as scanner:
                    report = await scanner.check_vulnerabilities(dependencies, severity_threshold)
                    return report

            # Run in a separate thread with its own event loop
            def run_in_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(scan())
                finally:
                    loop.close()

            with ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                report = future.result()

            return report.model_dump()

        except Exception as e:
            return {
                "error": str(e),
                "message": f"Failed to check vulnerabilities: {str(e)}",
            }

    @mcp_server.tool
    def generate_patch_preview(
        repo_path: str,
        upgrade_plan: dict,
    ) -> dict:
        """
        Generate a visual preview of proposed changes before applying.

        This tool creates a detailed diff showing exactly what will change in
        your manifest files (requirements.txt, package.json, etc.) if the
        upgrade plan is applied. Includes syntax-highlighted HTML visualization.

        Args:
            repo_path: Path to Databricks Repo
            upgrade_plan: Output from suggest_upgrades tool

        Returns:
            dict: {
                "repo_path": str,
                "upgrade_plan": {...},
                "files_to_modify": ["requirements.txt", "package.json"],
                "file_diffs": [
                    {
                        "file_path": "requirements.txt",
                        "diff_text": "--- a/requirements.txt\n+++ b/requirements.txt\n...",
                        "lines_added": 3,
                        "lines_removed": 3
                    }
                ],
                "visual_diff_html": "<html>...",  # Color-coded HTML diff
                "impact_summary": {
                    "total_changes": 6,
                    "breaking_changes": 0,
                    "files_modified": 2
                }
            }

        Example:
            generate_patch_preview(
                repo_path="/Repos/user@company.com/my-repo",
                upgrade_plan={...}
            )
        """
        try:
            # Get workspace client (use app-level auth for file access)
            w = utils.get_workspace_client()

            # Read current manifest files
            file_contents = {}

            # Determine which files to read based on ecosystems in upgrade plan
            ecosystems = set()
            for rec in upgrade_plan.get("recommendations", []):
                ecosystems.add(rec["ecosystem"])

            # Map ecosystems to file paths
            file_map = {
                "python": "requirements.txt",
                "javascript": "package.json",
                "java": "pom.xml",
                "r": "DESCRIPTION",
            }

            for ecosystem in ecosystems:
                if ecosystem in file_map:
                    file_name = file_map[ecosystem]
                    file_path = f"{repo_path}/{file_name}"

                    try:
                        content_bytes = w.workspace.download(file_path)
                        content = content_bytes.read().decode("utf-8")
                        file_contents[file_name] = content
                    except Exception:
                        pass  # File might not exist

            if not file_contents:
                return {
                    "error": "No manifest files found in repository",
                    "message": f"Could not read any manifest files from {repo_path}",
                }

            # Convert upgrade_plan dict to UpgradePlan model
            upgrade_plan_obj = UpgradePlan(**upgrade_plan)

            # Generate patch preview
            diff_gen = DiffGenerator()
            patch_preview = diff_gen.generate_patch_preview(
                repo_path, upgrade_plan_obj, file_contents
            )

            return patch_preview.model_dump()

        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to generate patch preview",
            }

    @mcp_server.tool
    def apply_security_patches(
        repo_path: str,
        upgrade_plan: dict,
        create_branch: bool = True,
        branch_name: str = "security-patches",
    ) -> dict:
        """
        Apply approved security patches to the repository.

        This tool modifies the manifest files in your repository to upgrade
        vulnerable packages to safe versions. Can optionally create a new
        Git branch for the changes.

        Note: When deployed to Databricks, changes sync to your Git provider.
        You may want to create a pull request through your Git provider's API.

        Args:
            repo_path: Path to Databricks Repo
            upgrade_plan: Approved upgrade plan from suggest_upgrades
            create_branch: Whether to create a new branch (default: True)
            branch_name: Name of branch to create (default: "security-patches")

        Returns:
            dict: {
                "status": "success",
                "repo_path": str,
                "branch": str,
                "files_modified": ["requirements.txt"],
                "packages_upgraded": 3,
                "message": "Security patches applied successfully"
            }

        Example:
            apply_security_patches(
                repo_path="/Repos/user@company.com/my-repo",
                upgrade_plan={...},
                create_branch=True,
                branch_name="fix-vulnerabilities"
            )
        """
        try:
            # Get workspace client (use app-level auth for file access)
            w = utils.get_workspace_client()

            # Get Git client
            git_client = DatabricksGitClient(w)

            # Get current branch
            current_branch = git_client.get_current_branch(repo_path)

            # Read current manifest files and generate modified versions
            file_contents = {}
            ecosystems = set()

            for rec in upgrade_plan.get("recommendations", []):
                ecosystems.add(rec["ecosystem"])

            file_map = {
                "python": "requirements.txt",
                "javascript": "package.json",
                "java": "pom.xml",
                "r": "DESCRIPTION",
            }

            for ecosystem in ecosystems:
                if ecosystem in file_map:
                    file_name = file_map[ecosystem]
                    file_path = f"{repo_path}/{file_name}"

                    try:
                        content_bytes = w.workspace.download(file_path)
                        content = content_bytes.read().decode("utf-8")
                        file_contents[file_name] = content
                    except Exception:
                        pass

            # Generate modified content using DiffGenerator
            upgrade_plan_obj = UpgradePlan(**upgrade_plan)
            diff_gen = DiffGenerator()

            file_changes = {}
            for file_name, original_content in file_contents.items():
                file_path_for_diff = file_name
                modified_content = diff_gen._apply_upgrades_to_content(
                    original_content, upgrade_plan_obj, file_path_for_diff
                )
                file_changes[file_name] = modified_content

            # Apply changes
            commit_message = (
                f"Apply security patches: upgrade {len(upgrade_plan['recommendations'])} packages"
            )

            success = git_client.apply_changes(repo_path, file_changes, commit_message)

            if success:
                return {
                    "status": "success",
                    "repo_path": repo_path,
                    "branch": current_branch or "unknown",
                    "files_modified": list(file_changes.keys()),
                    "packages_upgraded": len(upgrade_plan["recommendations"]),
                    "message": f"Security patches applied successfully. {len(file_changes)} files modified.",
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to apply changes to repository",
                }

        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to apply security patches",
            }

    @mcp_server.tool
    def get_vulnerability_details(cve_id: str) -> dict:
        """
        Fetch detailed information about a specific vulnerability.

        This tool retrieves comprehensive information about a CVE
        (Common Vulnerabilities and Exposures) identifier from the
        OSV.dev database.

        Args:
            cve_id: CVE identifier (e.g., "CVE-2023-32681")

        Returns:
            dict: {
                "cve_id": str,
                "severity": str,
                "cvss_score": float,
                "description": str,
                "affected_packages": [str],
                "affected_versions": [str],
                "fixed_versions": [str],
                "published_date": str,
                "references": [str],
                "exploit_available": bool
            }

        Example:
            get_vulnerability_details(cve_id="CVE-2023-32681")
        """
        try:

            async def fetch_details():
                async with VulnerabilityScanner() as scanner:
                    # Query OSV by CVE ID
                    payload = {"id": cve_id}

                    if scanner.session:
                        async with scanner.session.post(
                            "https://api.osv.dev/v1/vulns/" + cve_id
                        ) as response:
                            if response.status == 200:
                                data = await response.json()

                                # Parse vulnerability details
                                vulns = scanner._parse_osv_response({"vulns": [data]})

                                if vulns:
                                    vuln = vulns[0]
                                    return {
                                        "cve_id": vuln.cve_id,
                                        "severity": vuln.severity.value,
                                        "cvss_score": vuln.cvss_score,
                                        "description": vuln.description,
                                        "affected_versions": vuln.affected_versions,
                                        "fixed_versions": vuln.fixed_versions,
                                        "published_date": vuln.published_date,
                                        "references": vuln.references,
                                        "exploit_available": vuln.exploit_available,
                                    }

                    return {"error": "Vulnerability not found"}

            # Run in a separate thread with its own event loop
            def run_in_thread():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(fetch_details())
                finally:
                    loop.close()

            with ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                result = future.result()

            return result

        except Exception as e:
            return {
                "error": str(e),
                "message": f"Failed to fetch details for {cve_id}",
            }

    @mcp_server.tool
    def list_directory_contents(directory_path: str) -> dict:
        """
        List files in a Databricks workspace directory (diagnostic tool).

        This tool helps diagnose file access issues by showing what files
        are actually visible to the scanner in a given directory.

        Args:
            directory_path: Path to directory (e.g., /Workspace/Users/user@company.com/folder)

        Returns:
            dict: {
                "directory": str,
                "files": [list of file names],
                "total_items": int,
                "requirements_txt_present": bool
            }
        """
        try:
            w = utils.get_workspace_client()
            items = list(w.workspace.list(directory_path))

            files = []
            directories = []

            for item in items:
                if hasattr(item, "object_type"):
                    if item.object_type.name == "FILE":
                        files.append(item.path.split("/")[-1])
                    elif item.object_type.name == "DIRECTORY":
                        directories.append(item.path.split("/")[-1])

            # Try to read requirements.txt if it exists
            access_test = "not_attempted"
            if "requirements.txt" in files:
                try:
                    req_path = f"{directory_path}/requirements.txt"
                    content = w.workspace.download(req_path)
                    content_str = content.read().decode("utf-8")
                    access_test = f"✅ Can read requirements.txt ({len(content_str)} bytes)"
                except Exception as e:
                    access_test = f"❌ Cannot read requirements.txt: {str(e)}"

            return {
                "directory": directory_path,
                "files": files[:20],  # Limit to first 20 files
                "directories": directories[:10],  # Limit to first 10 dirs
                "total_items": len(files) + len(directories),
                "requirements_txt_present": "requirements.txt" in files,
                "access_test": access_test,
            }

        except Exception as e:
            return {
                "error": str(e),
                "message": f"Failed to list directory: {directory_path}",
            }

    # ========================================================================
    # ========================================================================
    # UNITY CATALOG INTEGRATION TOOLS
    # ========================================================================

    @mcp_server.tool
    def get_sca_findings_from_uc(
        catalog: str = "ing_hackathon",
        schema: str = "sca_advisor",
        status: str = "ready",
        priority: int = None,
        limit: int = 100,
    ) -> dict:
        """
        Get vulnerable repositories from Unity Catalog table.

        This tool reads from the UC table populated by Checkmarx or other
        vulnerability scanners. It's the entry point for the agent-based
        remediation workflow.

        Args:
            catalog: UC catalog name (default: "ing_hackathon")
            schema: UC schema name (default: "sca_advisor")
            status: Filter by status ('ready', 'analyzing', 'approved', 'rejected')
            priority: Filter by priority (1=Critical, 2=High, 3=Medium, None=all)
            limit: Maximum number of repos to return (default: 100)

        Returns:
            dict: {
                "repos": [
                    {
                        "repo_id": str,  # Unique ID for this repo+library
                        "repo_path": str,  # Databricks repo path
                        "repo_name": str,  # Human-readable name
                        "repo_url": str,  # Git URL for cloning
                        "library": str,  # Vulnerable library name
                        "current_version": str,  # Installed version
                        "priority": str,  # Critical, High, Medium, Low
                        "cve_ids": [str],  # List of CVE IDs
                        "cvss_score": float,  # CVSS severity
                        "candidate_versions": [
                            {"version": str, "vulnerability_count": int}
                        ],
                        "last_detected_ts": timestamp,
                        "status": str,
                        "checkmarx_finding_id": str,
                        "owner_team": str
                    }
                ],
                "total_repos": int
            }

        Example:
            get_sca_findings_from_uc(
                status="ready",
                priority=1,  # Critical only
                limit=10
            )

        Note:
            Requires PySpark (available in Databricks runtime).
            Will fail gracefully if run outside Databricks.
        """
        try:
            from services.uc_integration import UCIntegration

            uc = UCIntegration(catalog=catalog, schema=schema)
            repos = uc.get_sca_findings(status=status, priority=priority, limit=limit)

            return {
                "repos": repos,
                "total_repos": len(repos),
                "catalog": catalog,
                "schema": schema,
            }

        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to query UC table. Ensure running in Databricks environment.",
            }

    @mcp_server.tool
    def write_analysis_to_uc(
        repo_id: str,
        target_version: str,
        code_changes_files: int,
        code_changes_callsites: int,
        confidence: float,
        breaking_changes: list[str],
        notes: str = "",
        catalog: str = "ing_hackathon",
        schema: str = "sca_advisor",
    ) -> dict:
        """
        Write PYTHON package analysis results to Unity Catalog.

        **USE CASE:**
        - ✅ Writing Python package upgrade analysis results
        - ✅ Saving general vulnerability analysis results
        - ✅ Storing analysis for Python packages (NOT Java libraries)

        **WHEN TO USE:**
        - ✅ After analyzing Python packages
        - ✅ Writing general vulnerability analysis
        - ✅ Storing Python upgrade recommendations

        **WHEN NOT TO USE:**
        - ❌ Java library migration results → use `write_migration_analysis_to_uc`
        - ❌ Migration analysis with patches → use `write_migration_analysis_to_uc`

        After analyzing a repository's upgrade path, this tool saves the
        results to UC for review by the Streamlit UI and users.

        Args:
            repo_id: Repository ID from sca_findings table
            target_version: Version being analyzed (e.g., "2.31.0")
            code_changes_files: Number of files requiring changes
            code_changes_callsites: Number of call sites to modify
            confidence: Confidence score 0-1 (0.95 = high confidence)
            breaking_changes: List of breaking change descriptions
            notes: Additional notes or warnings
            catalog: UC catalog name
            schema: UC schema name

        Returns:
            dict: {
                "analysis_id": str,  # UUID
                "status": "success",
                "table": str
            }

        Example:
            write_analysis_to_uc(
                repo_id="repo_001",
                target_version="2.31.0",
                code_changes_files=3,
                code_changes_callsites=12,
                confidence=0.85,
                breaking_changes=["requests.packages removed"],
                notes="Manual review recommended for requests.packages usage"
            )
        """
        try:
            from services.uc_integration import UCIntegration

            uc = UCIntegration(catalog=catalog, schema=schema)
            analysis_id = uc.write_analysis_result(
                repo_id=repo_id,
                target_version=target_version,
                code_changes_files=code_changes_files,
                code_changes_callsites=code_changes_callsites,
                confidence=confidence,
                breaking_changes=breaking_changes,
                notes=notes,
            )

            return {
                "analysis_id": analysis_id,
                "status": "success",
                "table": f"{catalog}.{schema}.agent_analysis_results",
            }

        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to write analysis to UC",
            }

    @mcp_server.tool
    def record_user_decision_to_uc(
        repo_id: str,
        target_version: str,
        decision: str,
        user_email: str,
        decision_reason: str = "",
        catalog: str = "ing_hackathon",
        schema: str = "sca_advisor",
    ) -> dict:
        """
        Record user decision (approve/reject) to UC audit table.

        When a user reviews the agent's analysis and makes a decision,
        this tool records it for audit and tracking purposes.

        Args:
            repo_id: Repository ID
            target_version: Version decision applies to
            decision: 'approved' or 'rejected'
            user_email: Email of user making decision
            decision_reason: Reason for the decision
            catalog: UC catalog name
            schema: UC schema name

        Returns:
            dict: {
                "decision_id": str,  # UUID
                "status": "success"
            }

        Example:
            record_user_decision_to_uc(
                repo_id="repo_001",
                target_version="2.31.0",
                decision="approved",
                user_email="john.doe@company.com",
                decision_reason="Low risk, automated tests pass"
            )
        """
        try:
            from services.uc_integration import UCIntegration

            uc = UCIntegration(catalog=catalog, schema=schema)
            decision_id = uc.record_user_decision(
                repo_id=repo_id,
                target_version=target_version,
                decision=decision,
                user_email=user_email,
                decision_reason=decision_reason,
            )

            return {
                "decision_id": decision_id,
                "status": "success",
            }

        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to record decision to UC",
            }

    @mcp_server.tool
    def validate_patch_with_tests(
        repo_path: str,
        patch_content: str,
        run_tests: bool = True,
        test_command: str = "pytest tests/",
        create_test_branch: bool = True,
    ) -> dict:
        """
        Validate that a patch applies cleanly and optionally run tests.

        This tool is critical for ensuring patches don't break the codebase.
        It creates a test branch, applies the patch, runs tests, and reports results.

        Aligns with UC_INTEGRATION.md architecture (Patch Validator MCP).

        Args:
            repo_path: Path to repository (Databricks Repos or Workspace)
            patch_content: Unified diff patch content
            run_tests: Whether to run tests after applying patch
            test_command: Command to run tests (default: "pytest tests/")
            create_test_branch: Create temporary branch for testing

        Returns:
            dict: {
                "is_valid": bool,
                "applies_cleanly": bool,
                "tests_pass": bool,  # Only if run_tests=True
                "test_output": str,
                "errors": [str],
                "warnings": [str]
            }

        Example:
            validate_patch_with_tests(
                repo_path="/Workspace/Users/user@company.com/my-repo",
                patch_content="--- a/requirements.txt\\n+++ b/requirements.txt\\n...",
                run_tests=True
            )

        Note:
            Requires git and test framework (pytest, etc.) to be available.
            Cleans up test branch after validation.
        """
        try:
            import subprocess
            import tempfile
            import os

            errors = []
            warnings = []
            applies_cleanly = False
            tests_pass = None
            test_output = ""

            # Save patch to temporary file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
                f.write(patch_content)
                patch_file = f.name

            try:
                # Check if patch applies cleanly
                result = subprocess.run(
                    ["git", "apply", "--check", patch_file],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                applies_cleanly = result.returncode == 0

                if not applies_cleanly:
                    errors.append(f"Patch conflicts: {result.stderr}")
                else:
                    # Apply patch
                    subprocess.run(
                        ["git", "apply", patch_file],
                        cwd=repo_path,
                        check=True,
                        timeout=30,
                    )

                    # Run tests if requested
                    if run_tests:
                        test_result = subprocess.run(
                            test_command.split(),
                            cwd=repo_path,
                            capture_output=True,
                            text=True,
                            timeout=300,  # 5 minute timeout for tests
                        )

                        tests_pass = test_result.returncode == 0
                        test_output = test_result.stdout + test_result.stderr

                        if not tests_pass:
                            errors.append("Tests failed after applying patch")
                            warnings.append("Review test failures before approving patch")

                    # Revert patch (cleanup)
                    subprocess.run(
                        ["git", "apply", "--reverse", patch_file],
                        cwd=repo_path,
                        timeout=30,
                    )

            finally:
                # Clean up temp file
                os.unlink(patch_file)

            is_valid = applies_cleanly and (tests_pass if run_tests else True)

            return {
                "is_valid": is_valid,
                "applies_cleanly": applies_cleanly,
                "tests_pass": tests_pass,
                "test_output": test_output[:1000] if test_output else "",  # Limit output
                "errors": errors,
                "warnings": warnings,
            }

        except subprocess.TimeoutExpired:
            return {
                "is_valid": False,
                "applies_cleanly": False,
                "tests_pass": False,
                "errors": ["Operation timed out"],
                "warnings": [],
            }
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to validate patch",
            }

    @mcp_server.tool
    def clone_github_repo(
        git_url: str,
        provider: str = "github",
        branch: str = "main",
        user_email: str = "adminuser4510846@vocareum.com",
        destination_folder: str = "repos",
    ) -> dict:
        """
        Clone a GitHub repository to Databricks /Repos/ workspace.

        This tool clones a remote Git repository to your Databricks workspace
        for code analysis, vulnerability scanning, or other operations.
        Use scan_repo_dependencies separately after cloning if you want to scan.

        The repository is cloned to: /Repos/{user_email}/{destination_folder}/{repo_name}

        Args:
            git_url: GitHub repository URL (e.g., "https://github.com/org/repo.git")
            provider: Git provider - "github", "gitLab", "bitbucketCloud", or "azureDevOpsServices"
            branch: Branch to checkout (default: "main")
            user_email: User email for repo path (default: "adminuser4510846@vocareum.com")
            destination_folder: Folder name under /Repos/{user_email}/ (default: "repos")

        Returns:
            dict: {
                "status": "success" | "error",
                "repo_name": str,
                "repo_path": str,
                "branch": str,
                "url": str,
                "commit": str,
                "message": str
            }

        Example:
            # Clone a repository
            result = clone_github_repo(
                git_url="https://github.com/databricks/databricks-sdk-py.git",
                destination_folder="hackathon_databricks"
            )

            # Then scan it separately if needed
            scan_result = scan_repo_dependencies(repo_path=result["repo_path"])
        """
        try:
            # Get workspace client
            w = utils.get_workspace_client()
            git_client = DatabricksGitClient(w)

            # Extract repo name from URL
            repo_name = git_url.rstrip(".git").split("/")[-1]

            # Build repo path
            repo_path = f"/Repos/{user_email}/{destination_folder}/{repo_name}"

            # Clone repository
            repo = git_client.clone_repo(
                git_url=git_url, workspace_path=repo_path, provider=provider, branch=branch
            )

            if not repo:
                return {
                    "status": "error",
                    "message": f"Failed to clone repository from {git_url}. Check URL and credentials.",
                }

            # Return repository information
            return {
                "status": "success",
                "repo_name": repo_name,
                "repo_path": repo.path,
                "branch": repo.branch,
                "url": git_url,
                "commit": repo.head_commit_id,
                "message": (
                    f"✅ Successfully cloned {repo_name} to {repo.path}. "
                    f"Use scan_repo_dependencies('{repo.path}') to scan for vulnerabilities."
                ),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error cloning repository: {str(e)}",
                "error": str(e),
            }

    @mcp_server.tool
    def get_library_migration_analysis(
        source_repo_url: str,
        library_name: str,
        current_version: str,
        target_version: str,
        library_repo_url: str = None,
        source_branch: str = "main",
    ) -> dict:
        """
        ⭐ PRIMARY TOOL FOR JAVA LIBRARY MIGRATION WORKFLOW

        Analyze library migration and return breaking changes with source code context.

        **USE CASE:**
        - ✅ Analyzing Java library version upgrades (e.g., Spring Boot 2.7 → 3.0)
        - ✅ Need breaking changes + source context for LLM code generation
        - ✅ Migration planning and impact analysis

        **WHEN TO USE:**
        - ✅ You have a Java library to upgrade (current_version → target_version)
        - ✅ You need to know what code changes are required
        - ✅ You're preparing data for LLM to generate migration patches

        **WHEN NOT TO USE:**
        - ❌ General vulnerability scanning → use `check_vulnerabilities`
        - ❌ Python package analysis → use `analyze_package_usage`
        - ❌ General Java code analysis → use `analyze_java_repos_from_uc`
        - ❌ Python API changes → use `check_api_changes`

        **AGENT WORKFLOW:**
        1. Call this tool to get breaking_changes[] + source_context[]
        2. Use LLM to generate patches from breaking_changes
        3. Call `write_migration_analysis_to_uc()` to save results

        This tool analyzes what code changes are needed to migrate from library version L1
        to L2. It returns structured data (breaking changes + source context) for the agent
        to use with LLM for code generation.

        **This tool does NOT generate code patches** - that's the agent's responsibility.
        The agent will use the returned data to call LLM and generate patches.

        What this tool does:
        1. Clones source repo + library L1 + library L2 (temporary, auto-cleanup)
        2. Parses source code to find library method invocations
        3. Extracts API declarations from library L1 and L2
        4. Compares L1 vs L2 to detect breaking changes
        5. Cross-references breaking changes with source code usage
        6. Returns structured data with full source context

        Args:
            source_repo_url: Git URL of source code (e.g., "https://github.com/org/app.git")
            library_name: Library being upgraded (e.g., "spring-boot")
            current_version: Current version in source code (e.g., "2.7.0")
            target_version: Target upgrade version (e.g., "3.0.0")
            library_repo_url: Optional GitHub URL of library (auto-resolved if not provided)
            source_branch: Branch to analyze (default: "main")

        Returns:
            dict: {
                "status": "success" | "error",
                "library": str,
                "from_version": str,
                "to_version": str,
                "breaking_changes": [
                    {
                        "id": str,
                        "class": str,
                        "method": str,
                        "change_type": str,  # "signature_changed", "method_removed", etc.
                        "old_signature": str,
                        "new_signature": str,
                        "change_description": str,
                        "affected_locations": [
                            {
                                "file": str,
                                "line": int,
                                "column": int,
                                "source_context": {
                                    "target_line": str,
                                    "surrounding_context": str,
                                    "full_method": str,
                                    "class_name": str,
                                    "package": str,
                                    "imports": list
                                }
                            }
                        ]
                    }
                ],
                "summary": {
                    "breaking_changes_count": int,
                    "affected_files": int,
                    "affected_invocations": int,
                    "unique_classes_changed": int,
                    "unique_methods_changed": int
                },
                "metadata": {
                    "source_files_analyzed": int,
                    "library_files_analyzed": {"v1": int, "v2": int}
                }
            }

        Example:
            # Agent calls this tool
            result = get_library_migration_analysis(
                source_repo_url="https://github.com/mycompany/customer-service.git",
                library_name="spring-boot",
                current_version="2.7.0",
                target_version="3.0.0"
            )

            # Agent then uses result["breaking_changes"] with LLM to generate patches
            for breaking_change in result["breaking_changes"]:
                for location in breaking_change["affected_locations"]:
                    # Build LLM prompt from breaking_change + location["source_context"]
                    patch = llm.generate_patch(...)

        Note:
            - Uses temporary cloning (auto-cleanup)
            - No LLM calls in this tool
            - Returns structured data ready for agent to process
        """
        from services.library_migration_analyzer import LibraryMigrationAnalyzer

        try:
            w = utils.get_workspace_client()
            analyzer = LibraryMigrationAnalyzer(w)

            result = analyzer.analyze_migration(
                source_repo_url=source_repo_url,
                library_name=library_name,
                current_version=current_version,
                target_version=target_version,
                library_repo_url=library_repo_url,
                source_branch=source_branch,
            )

            return result

        except Exception as e:
            logger.error(f"❌ Library migration analysis failed: {e}")
            return {
                "status": "error",
                "message": f"Migration analysis failed: {str(e)}",
                "error": str(e),
            }

    @mcp_server.tool
    def write_migration_analysis_to_uc(
        repo_id: str,
        library: str,
        from_version: str,
        to_version: str,
        breaking_changes: list,
        patches: list,
        summary: dict,
        catalog: str = "ing_hackathon",
        schema: str = "sca_advisor",
    ) -> dict:
        """
        ⭐ PRIMARY TOOL FOR JAVA LIBRARY MIGRATION WORKFLOW

        Write library migration analysis results to Unity Catalog.

        **USE CASE:**
        - ✅ Writing migration analysis results (breaking changes + LLM-generated patches)
        - ✅ Saving results for Streamlit UI to display
        - ✅ Storing migration analysis for audit trail

        **WHEN TO USE:**
        - ✅ After calling `get_library_migration_analysis()` and generating patches with LLM
        - ✅ When you have breaking_changes[] and patches[] ready to save
        - ✅ Before displaying results to user in Streamlit UI

        **WHEN NOT TO USE:**
        - ❌ Writing Python package analysis → use `write_analysis_to_uc`
        - ❌ Writing general vulnerability results → use `write_analysis_to_uc`

        **AGENT WORKFLOW:**
        1. Call `get_library_migration_analysis()` to get breaking changes
        2. Use LLM to generate patches
        3. Call this tool to write results to UC

        After the agent generates patches using LLM, this tool writes the complete
        analysis (breaking changes + generated patches) to UC for the Streamlit app
        to display.

        Args:
            repo_id: Repository ID from sca_findings table
            library: Library name (e.g., "spring-boot")
            from_version: Current version (e.g., "2.7.0")
            to_version: Target version (e.g., "3.0.0")
            breaking_changes: List of breaking changes from get_library_migration_analysis
            patches: List of patches generated by agent (LLM-generated code)
            summary: Summary statistics from get_library_migration_analysis
            catalog: UC catalog name
            schema: UC schema name

        Patches structure (generated by agent):
            [
                {
                    "file": str,
                    "line": int,
                    "old_code": str,
                    "new_code": str,
                    "confidence": "high" | "medium" | "low",
                    "explanation": str,
                    "generated_by": str,  # LLM model name
                    "generation_timestamp": str
                }
            ]

        Returns:
            dict: {
                "status": "success",
                "analysis_id": str,  # UUID
                "message": str
            }

        Example:
            # Agent workflow:
            # 1. Get breaking changes
            analysis = get_library_migration_analysis(...)

            # 2. Generate patches with LLM
            patches = []
            for breaking_change in analysis["breaking_changes"]:
                patch = llm.generate_patch(...)
                patches.append(patch)

            # 3. Write to UC
            write_migration_analysis_to_uc(
                repo_id="repo_123",
                library="spring-boot",
                from_version="2.7.0",
                to_version="3.0.0",
                breaking_changes=analysis["breaking_changes"],
                patches=patches,
                summary=analysis["summary"]
            )
        """
        from services.uc_integration import UCIntegration

        try:
            uc = UCIntegration(catalog=catalog, schema=schema)

            # Calculate additional summary metrics
            patches_high = sum(1 for p in patches if p.get("confidence") == "high")
            patches_medium = sum(1 for p in patches if p.get("confidence") == "medium")
            patches_low = sum(1 for p in patches if p.get("confidence") == "low")

            # Determine migration complexity
            if summary["breaking_changes_count"] <= 3 and summary["affected_files"] <= 2:
                complexity = "low"
            elif summary["breaking_changes_count"] <= 10 and summary["affected_files"] <= 5:
                complexity = "medium"
            else:
                complexity = "high"

            # Estimate effort (rough heuristic)
            estimated_hours = (
                summary["breaking_changes_count"] * 0.1 + summary["affected_files"] * 0.3
            )

            # Auto-fixable percentage (based on confidence)
            total_patches = len(patches)
            if total_patches > 0:
                auto_fixable = (patches_high / total_patches) * 100
            else:
                auto_fixable = 0.0

            # Write to UC
            analysis_id = uc.write_migration_analysis(
                repo_id=repo_id,
                library=library,
                from_version=from_version,
                to_version=to_version,
                breaking_changes=breaking_changes,
                patches=patches,
                summary={
                    **summary,
                    "patches_generated": total_patches,
                    "patches_high_confidence": patches_high,
                    "patches_medium_confidence": patches_medium,
                    "patches_low_confidence": patches_low,
                    "migration_complexity": complexity,
                    "estimated_effort_hours": estimated_hours,
                    "auto_fixable_percent": auto_fixable,
                },
            )

            return {
                "status": "success",
                "analysis_id": analysis_id,
                "message": f"Migration analysis written to {catalog}.{schema}.migration_analysis_results",
            }

        except Exception as e:
            logger.error(f"❌ Failed to write migration analysis to UC: {e}")
            return {
                "status": "error",
                "message": f"Failed to write to UC: {str(e)}",
                "error": str(e),
            }

    @mcp_server.tool
    def generate_migration_code_diff(
        source_repo_url: str,
        library_name: str,
        current_version: str,
        target_version: str,
        library_repo_url: str = None,
        source_branch: str = "main",
    ) -> dict:
        """
        Generate actual code diffs for migrating to a new library version.

        **THIS IS THE KEY TOOL FOR CODE MIGRATION!**

        This tool performs end-to-end analysis and generates actual code changes
        (not just TODOs or comments) for upgrading a vulnerable library.

        **WHEN TO USE:**
        - ✅ When you need to generate the actual code changes for a library upgrade
        - ✅ After identifying a vulnerable library that needs upgrading
        - ✅ When the user asks "what code changes are needed?"
        - ✅ When preparing a migration plan with concrete fixes

        **WHAT THIS TOOL DOES:**
        1. Clones the source repository
        2. Analyzes all Java files for library usage
        3. Clones both library versions (current and target)
        4. Detects breaking API changes between versions
        5. **Generates actual code transformations** for each affected location
        6. Returns unified diffs ready to apply

        **SUPPORTED TRANSFORMATIONS:**
        - Method renames → Automatic replacement
        - Removed methods → Suggests alternatives (FIXME comments if unknown)
        - Signature changes → Adds default parameters
        - Type migrations → Adds appropriate casts/conversions
        - Import updates → Identifies new imports needed

        Args:
            source_repo_url: Git URL of source code repository
            library_name: Library being upgraded (e.g., "jackson-databind")
            current_version: Current version (e.g., "2.9.8")
            target_version: Target version (e.g., "2.15.0")
            library_repo_url: Optional GitHub URL of library (auto-resolved if not provided)
            source_branch: Branch to analyze (default: "main")

        Returns:
            dict: {
                "status": "success",
                "library": "jackson-databind",
                "from_version": "2.9.8",
                "to_version": "2.15.0",
                "file_diffs": [
                    {
                        "file_path": "src/main/java/com/example/Service.java",
                        "diff_text": "--- a/src/main/java/...\\n+++ b/src/main/java/...",
                        "lines_added": 5,
                        "lines_removed": 3
                    }
                ],
                "fixes_applied": [
                    {
                        "file": "src/main/java/com/example/Service.java",
                        "line": 42,
                        "change_type": "method_removed",
                        "description": "Replaced removed method 'enableDefaultTyping' with 'activateDefaultTyping'",
                        "confidence": 0.9,
                        "original": "mapper.enableDefaultTyping();",
                        "fixed": "mapper.activateDefaultTyping(...);"
                    }
                ],
                "summary": {
                    "files_modified": 3,
                    "total_fixes": 7,
                    "lines_added": 15,
                    "lines_removed": 12,
                    "average_confidence": 0.82,
                    "requires_manual_review": true
                },
                "visual_diff_html": "<html>..."
            }

        Example:
            # Generate migration diff for jackson-databind upgrade
            result = generate_migration_code_diff(
                source_repo_url="https://github.com/company/payment-service.git",
                library_name="jackson-databind",
                current_version="2.9.8",
                target_version="2.15.0"
            )

            # The result contains actual diffs ready to apply
            for diff in result["file_diffs"]:
                print(f"Changes for {diff['file_path']}:")
                print(diff["diff_text"])
        """
        from services.library_migration_analyzer import LibraryMigrationAnalyzer
        from services.diff_generator import DiffGenerator
        import tempfile
        from pathlib import Path

        try:
            w = utils.get_workspace_client()
            migration_analyzer = LibraryMigrationAnalyzer(w)
            diff_generator = DiffGenerator()

            logger.info(
                f"🔄 Starting migration diff generation: {library_name} {current_version} → {target_version}"
            )

            # Step 1: Analyze migration to get breaking changes
            analysis_result = migration_analyzer.analyze_migration(
                source_repo_url=source_repo_url,
                library_name=library_name,
                current_version=current_version,
                target_version=target_version,
                library_repo_url=library_repo_url,
                source_branch=source_branch,
            )

            if analysis_result.get("status") == "error":
                return analysis_result

            breaking_changes = analysis_result.get("breaking_changes", [])

            if not breaking_changes:
                return {
                    "status": "success",
                    "message": "No breaking changes detected - migration should be safe",
                    "library": library_name,
                    "from_version": current_version,
                    "to_version": target_version,
                    "file_diffs": [],
                    "fixes_applied": [],
                    "summary": {
                        "files_modified": 0,
                        "total_fixes": 0,
                        "lines_added": 0,
                        "lines_removed": 0,
                        "average_confidence": 1.0,
                        "requires_manual_review": False,
                    },
                }

            # Step 2: Clone source repo to get file contents
            with tempfile.TemporaryDirectory() as temp_dir:
                import subprocess
                import shutil

                source_path = Path(temp_dir) / "source"

                # Clone source repo
                cmd = [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    source_branch,
                    source_repo_url,
                    str(source_path),
                ]
                try:
                    subprocess.run(cmd, check=True, capture_output=True, text=True)
                except subprocess.CalledProcessError:
                    # Fallback without branch
                    subprocess.run(
                        ["git", "clone", "--depth", "1", source_repo_url, str(source_path)],
                        check=True,
                        capture_output=True,
                        text=True,
                    )

                # Collect affected source files
                source_files = {}
                for bc in breaking_changes:
                    for location in bc.get("affected_locations", []):
                        file_path = location.get("file", "")
                        if file_path and file_path not in source_files:
                            full_path = source_path / file_path
                            if full_path.exists():
                                try:
                                    source_files[file_path] = full_path.read_text(encoding="utf-8")
                                except UnicodeDecodeError:
                                    source_files[file_path] = full_path.read_text(
                                        encoding="latin-1", errors="replace"
                                    )

                if not source_files:
                    return {
                        "status": "warning",
                        "message": "Breaking changes detected but no source files found at affected locations",
                        "library": library_name,
                        "from_version": current_version,
                        "to_version": target_version,
                        "breaking_changes": breaking_changes,
                        "file_diffs": [],
                        "fixes_applied": [],
                    }

                # Step 3: Generate code diffs
                result = diff_generator.generate_java_migration_diff(
                    breaking_changes=breaking_changes,
                    source_files=source_files,
                    library_name=library_name,
                    current_version=current_version,
                    target_version=target_version,
                )

                # Add metadata from analysis
                result["metadata"] = analysis_result.get("metadata", {})
                result["breaking_changes_detected"] = len(breaking_changes)

                logger.info(
                    f"✅ Generated migration diff: {result['summary']['total_fixes']} fixes in {result['summary']['files_modified']} files"
                )

                return result

        except Exception as e:
            logger.error(f"❌ Failed to generate migration code diff: {e}")
            import traceback

            traceback.print_exc()
            return {
                "status": "error",
                "message": f"Failed to generate migration diff: {str(e)}",
                "library": library_name,
                "from_version": current_version,
                "to_version": target_version,
                "error": str(e),
            }
