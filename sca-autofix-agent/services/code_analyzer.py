"""
Code analyzer service for extracting dependencies from source code.
"""

import json
import re
import tomli
from pathlib import Path
from typing import Optional

from databricks.sdk import WorkspaceClient

from models import DependencyInfo, PackageEcosystem


class CodeAnalyzer:
    """Analyzes source code to extract dependency information."""

    def __init__(self, workspace_client: WorkspaceClient):
        """
        Initialize the code analyzer.

        Args:
            workspace_client: Authenticated Databricks workspace client
        """
        self.workspace_client = workspace_client

    def scan_repository(
        self, repo_path: str, branch: str = "main"
    ) -> DependencyInfo:
        """
        Scan a Databricks repository to extract all dependencies.

        Args:
            repo_path: Path to Databricks Repo (e.g., /Repos/user@company.com/my-repo)
            branch: Git branch to scan

        Returns:
            DependencyInfo: Complete dependency information
        """
        packages = {
            "python": {},
            "javascript": {},
            "java": {},
            "r": {},
        }
        manifest_files = []

        # Python dependencies
        python_deps = self._extract_python_dependencies(repo_path)
        if python_deps:
            packages["python"].update(python_deps)
            manifest_files.extend(
                [f for f in ["requirements.txt", "pyproject.toml", "setup.py"] if python_deps]
            )

        # JavaScript/Node.js dependencies
        js_deps = self._extract_javascript_dependencies(repo_path)
        if js_deps:
            packages["javascript"].update(js_deps)
            manifest_files.append("package.json")

        # Java dependencies
        java_deps = self._extract_java_dependencies(repo_path)
        if java_deps:
            packages["java"].update(java_deps)
            manifest_files.append("pom.xml")

        # R dependencies
        r_deps = self._extract_r_dependencies(repo_path)
        if r_deps:
            packages["r"].update(r_deps)
            manifest_files.append("DESCRIPTION")

        # Remove empty ecosystems
        packages = {k: v for k, v in packages.items() if v}

        total_packages = sum(len(deps) for deps in packages.values())

        return DependencyInfo(
            repo_path=repo_path,
            branch=branch,
            packages=packages,
            manifest_files=list(set(manifest_files)),
            total_packages=total_packages,
        )

    def _extract_python_dependencies(self, repo_path: str) -> dict[str, str]:
        """Extract Python dependencies from requirements.txt and pyproject.toml."""
        dependencies = {}

        # Try requirements.txt
        try:
            requirements_path = f"{repo_path}/requirements.txt"
            print(f"🔍 Checking for requirements.txt at: {requirements_path}")
            content = self._read_workspace_file(requirements_path)
            if content:
                parsed = self._parse_requirements_txt(content)
                print(f"✅ Parsed {len(parsed)} packages from requirements.txt")
                dependencies.update(parsed)
            else:
                print("⚠️ requirements.txt not found or empty")
        except Exception as e:
            print(f"❌ Error reading requirements.txt: {e}")
            pass  # File might not exist

        # Try pyproject.toml
        try:
            pyproject_path = f"{repo_path}/pyproject.toml"
            print(f"🔍 Checking for pyproject.toml at: {pyproject_path}")
            content = self._read_workspace_file(pyproject_path)
            if content:
                parsed = self._parse_pyproject_toml(content)
                print(f"✅ Parsed {len(parsed)} packages from pyproject.toml")
                dependencies.update(parsed)
            else:
                print("⚠️ pyproject.toml not found or empty")
        except Exception as e:
            print(f"❌ Error reading pyproject.toml: {e}")
            pass

        return dependencies

    def _parse_requirements_txt(self, content: str) -> dict[str, str]:
        """Parse requirements.txt format."""
        dependencies = {}
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Handle various formats: package==1.0.0, package>=1.0.0, package, package[extra]
            # Remove comments at end of line
            if "#" in line:
                line = line.split("#")[0].strip()
            
            # Extract package name (handle extras like ray[default])
            match = re.match(r"^([a-zA-Z0-9_-]+)(?:\[[^\]]+\])?(?:==|>=|<=|>|<|~=)?([0-9.]+)?", line)
            if match:
                package_name = match.group(1)
                version = match.group(2) if match.group(2) else "latest"
                dependencies[package_name] = version

        return dependencies

    def _parse_pyproject_toml(self, content: str) -> dict[str, str]:
        """Parse pyproject.toml format."""
        dependencies = {}
        try:
            data = tomli.loads(content)

            # Check [project.dependencies]
            if "project" in data and "dependencies" in data["project"]:
                for dep in data["project"]["dependencies"]:
                    match = re.match(r"^([a-zA-Z0-9_-]+)(?:==|>=|<=|>|<|~=)?([0-9.]+)?", dep)
                    if match:
                        package_name = match.group(1)
                        version = match.group(2) if match.group(2) else "latest"
                        dependencies[package_name] = version

            # Check [tool.poetry.dependencies]
            if "tool" in data and "poetry" in data["tool"]:
                poetry_deps = data["tool"]["poetry"].get("dependencies", {})
                for package, version_spec in poetry_deps.items():
                    if package == "python":
                        continue
                    if isinstance(version_spec, str):
                        # Extract version number from spec like "^1.0.0"
                        version_match = re.search(r"([0-9.]+)", version_spec)
                        version = version_match.group(1) if version_match else "latest"
                        dependencies[package] = version

        except Exception:
            pass  # Parsing error

        return dependencies

    def _extract_javascript_dependencies(self, repo_path: str) -> dict[str, str]:
        """Extract JavaScript dependencies from package.json."""
        dependencies = {}

        try:
            package_json_path = f"{repo_path}/package.json"
            content = self._read_workspace_file(package_json_path)
            if content:
                data = json.loads(content)
                
                # Merge dependencies and devDependencies
                for dep_type in ["dependencies", "devDependencies"]:
                    if dep_type in data:
                        for package, version in data[dep_type].items():
                            # Clean version string (remove ^, ~, etc.)
                            clean_version = re.sub(r"[^0-9.]", "", version)
                            dependencies[package] = clean_version if clean_version else "latest"

        except Exception:
            pass

        return dependencies

    def _extract_java_dependencies(self, repo_path: str) -> dict[str, str]:
        """Extract Java dependencies from pom.xml."""
        dependencies = {}

        try:
            pom_path = f"{repo_path}/pom.xml"
            content = self._read_workspace_file(pom_path)
            if content:
                # Simple XML parsing for Maven dependencies
                # Format: <groupId>org.apache.spark</groupId><artifactId>spark-core</artifactId><version>3.5.0</version>
                pattern = r"<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>\s*<version>([^<]+)</version>"
                matches = re.findall(pattern, content, re.DOTALL)

                for group_id, artifact_id, version in matches:
                    package_name = f"{group_id.strip()}:{artifact_id.strip()}"
                    dependencies[package_name] = version.strip()

        except Exception:
            pass

        return dependencies

    def _extract_r_dependencies(self, repo_path: str) -> dict[str, str]:
        """Extract R dependencies from DESCRIPTION file."""
        dependencies = {}

        try:
            description_path = f"{repo_path}/DESCRIPTION"
            content = self._read_workspace_file(description_path)
            if content:
                # Parse DESCRIPTION file format
                in_imports = False
                for line in content.split("\n"):
                    if line.startswith("Imports:"):
                        in_imports = True
                        line = line.replace("Imports:", "").strip()

                    if in_imports:
                        if line and not line[0].isspace() and ":" in line:
                            in_imports = False
                            continue

                        # Parse package (>= version) format
                        match = re.match(r"^\s*([a-zA-Z0-9.]+)\s*(?:\(>=\s*([0-9.]+)\))?", line)
                        if match:
                            package_name = match.group(1)
                            version = match.group(2) if match.group(2) else "latest"
                            dependencies[package_name] = version

        except Exception:
            pass

        return dependencies

    def _read_workspace_file(self, file_path: str) -> Optional[str]:
        """
        Read a file from Databricks workspace.

        Args:
            file_path: Full path to the file in workspace

        Returns:
            File content as string, or None if file doesn't exist
        """
        try:
            # Use workspace API to download file content
            content_bytes = self.workspace_client.workspace.download(file_path)
            content = content_bytes.read().decode("utf-8")
            print(f"✅ Successfully read {file_path} ({len(content)} bytes)")
            return content
        except Exception as e:
            print(f"⚠️ Failed to read {file_path}: {type(e).__name__}: {str(e)}")
            return None

