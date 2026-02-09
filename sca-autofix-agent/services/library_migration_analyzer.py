"""
Library migration analyzer for comparing library versions and finding breaking changes.

This service analyzes library migrations by:
1. Cloning source code + 2 library versions (temp)
2. Parsing Java code to find method invocations
3. Extracting API declarations from both library versions
4. Comparing declarations to detect breaking changes
5. Cross-referencing with source code usage

Returns structured data for agent to use with LLM (no LLM calls here).
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

from databricks.sdk import WorkspaceClient
from services.java_analyzer import JavaAnalyzer
from services.git_client import DatabricksGitClient

logger = logging.getLogger(__name__)


class LibraryMigrationAnalyzer:
    """Analyze library migrations and return breaking changes with source context."""

    def __init__(self, workspace_client: WorkspaceClient):
        """Initialize the migration analyzer."""
        self.w = workspace_client
        self.java_analyzer = JavaAnalyzer(workspace_client)
        self.git_client = DatabricksGitClient(workspace_client)

    def analyze_migration(
        self,
        source_repo_url: str,
        library_name: str,
        current_version: str,
        target_version: str,
        library_repo_url: Optional[str] = None,
        source_branch: str = "main",
    ) -> Dict[str, Any]:
        """
        Analyze library migration and return breaking changes with source context.

        This method does NOT generate code patches - that's the agent's job.
        Returns structured data for the agent to use with LLM.

        Args:
            source_repo_url: Git URL of source code repository
            library_name: Library being upgraded (e.g., "spring-boot")
            current_version: Current version in source code (e.g., "2.7.0")
            target_version: Target upgrade version (e.g., "3.0.0")
            library_repo_url: Optional GitHub URL of library (auto-resolved if not provided)
            source_branch: Branch to analyze (default: "main")

        Returns:
            dict: {
                "status": "success",
                "breaking_changes": [...],
                "summary": {...},
                "metadata": {...}
            }
        """
        logger.info(f"🔍 Analyzing migration: {library_name} {current_version} → {target_version}")

        # Resolve library GitHub URL if not provided
        if not library_repo_url:
            library_repo_url = self._resolve_library_github_url(library_name)
            if not library_repo_url:
                return {
                    "status": "error",
                    "message": f"Could not resolve GitHub URL for library {library_name}",
                }

        # Use temporary directory for all clones
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            try:
                # Step 1: Clone source repo
                logger.info(f"📥 Cloning source repo: {source_repo_url}")
                source_path = temp_path / "source"
                self._clone_repo(source_repo_url, source_path, source_branch)

                # Step 2: Clone library L1 (current version)
                logger.info(f"📥 Cloning library L1: {library_repo_url} @ {current_version}")
                library_v1_path = temp_path / "library_v1"
                self._clone_repo(library_repo_url, library_v1_path, current_version)

                # Step 3: Clone library L2 (target version)
                logger.info(f"📥 Cloning library L2: {library_repo_url} @ {target_version}")
                library_v2_path = temp_path / "library_v2"
                self._clone_repo(library_repo_url, library_v2_path, target_version)

                # Step 4: Parse source code to find library usage
                logger.info("🔍 Parsing source code...")
                source_invocations = self._parse_source_invocations(source_path, library_name)

                # Step 5: Extract library declarations (L1 and L2)
                logger.info("📚 Extracting library declarations...")
                l1_declarations = self._extract_library_declarations(library_v1_path, library_name)
                l2_declarations = self._extract_library_declarations(library_v2_path, library_name)

                # Step 6: Compare declarations to find breaking changes
                logger.info("🔬 Comparing library versions...")
                breaking_changes = self._compare_declarations(
                    l1_declarations, l2_declarations, library_name
                )

                # Step 7: Cross-reference with source code
                logger.info("🔗 Cross-referencing with source code...")
                breaking_changes_with_context = self._add_source_context(
                    breaking_changes, source_invocations, source_path
                )

                # Step 8: Generate summary
                summary = self._generate_summary(breaking_changes_with_context)

                logger.info(
                    f"✅ Analysis complete: {summary['breaking_changes_count']} breaking changes, "
                    f"{summary['affected_files']} files affected"
                )

                return {
                    "status": "success",
                    "library": library_name,
                    "from_version": current_version,
                    "to_version": target_version,
                    "breaking_changes": breaking_changes_with_context,
                    "summary": summary,
                    "metadata": {
                        "source_files_analyzed": len(source_invocations),
                        "library_files_analyzed": {
                            "v1": len(l1_declarations.get("methods", [])),
                            "v2": len(l2_declarations.get("methods", [])),
                        },
                    },
                }

            except Exception as e:
                logger.error(f"❌ Migration analysis failed: {e}")
                return {
                    "status": "error",
                    "message": f"Migration analysis failed: {str(e)}",
                    "error": str(e),
                }

    def _clone_repo(self, repo_url: str, dest: Path, ref: str) -> None:
        """Clone repository to destination path."""
        import subprocess
        import shutil

        if dest.exists():
            shutil.rmtree(dest)

        cmd = ["git", "clone", "--depth", "1"]

        if ref:
            cmd += ["--branch", ref, "--single-branch"]

        cmd += [repo_url, str(dest)]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError:
            # Fallback: clone default branch, then checkout
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, str(dest)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "checkout", ref],
                cwd=dest,
                check=True,
                capture_output=True,
                text=True,
            )

    def _parse_source_invocations(
        self, source_path: Path, library_package: str
    ) -> List[Dict[str, Any]]:
        """Parse source code and find all method invocations from the library."""
        # Use JavaAnalyzer to parse source code
        # This returns method invocations with context
        invocations = []

        # Find all Java files
        java_files = list(source_path.rglob("*.java"))

        for java_file in java_files:
            try:
                result = self.java_analyzer._analyze_java_file(java_file, source_path)

                if result["parse_ok"]:
                    for inv in result["invocations"]:
                        # Filter for library package
                        if self._is_library_method(inv, library_package):
                            invocations.append(inv)

            except Exception as e:
                logger.warning(f"⚠️ Failed to parse {java_file}: {e}")

        return invocations

    def _is_library_method(self, invocation: Dict[str, Any], library_package: str) -> bool:
        """Check if invocation is from the target library."""
        # Simple heuristic: check if qualifier or package matches
        qualifier = invocation.get("callee_qualifier", "")
        # This is a simplified check - in production, you'd need more sophisticated matching
        return library_package.lower() in qualifier.lower() if qualifier else False

    def _extract_library_declarations(
        self, library_path: Path, library_name: str
    ) -> Dict[str, Any]:
        """Extract public API declarations from library source code."""
        import javalang

        declarations = {
            "classes": [],
            "methods": [],
            "interfaces": [],
        }

        java_files = list(library_path.rglob("*.java"))

        for java_file in java_files:
            try:
                source = java_file.read_text(encoding="utf-8")
                tree = javalang.parse.parse(source)

                # Extract class declarations
                for type_decl in tree.types or []:
                    if hasattr(type_decl, "name"):
                        declarations["classes"].append(
                            {
                                "name": type_decl.name,
                                "package": tree.package.name if tree.package else None,
                                "kind": type_decl.__class__.__name__,
                            }
                        )

                    # Extract method declarations
                    if hasattr(type_decl, "methods"):
                        for method in type_decl.methods or []:
                            if hasattr(method, "name") and hasattr(method, "parameters"):
                                method_sig = self._build_method_signature(method)
                                declarations["methods"].append(
                                    {
                                        "class": type_decl.name,
                                        "package": tree.package.name if tree.package else None,
                                        "name": method.name,
                                        "signature": method_sig,
                                        "parameters": [
                                            {
                                                "type": str(param.type),
                                                "name": param.name,
                                            }
                                            for param in method.parameters
                                        ],
                                        "return_type": str(method.return_type)
                                        if hasattr(method, "return_type")
                                        else None,
                                    }
                                )

            except Exception as e:
                logger.warning(f"⚠️ Failed to parse library file {java_file}: {e}")

        return declarations

    def _build_method_signature(self, method) -> str:
        """Build method signature string from AST node."""
        params = ", ".join([f"{param.type} {param.name}" for param in method.parameters])
        return_type = str(method.return_type) if hasattr(method, "return_type") else "void"
        return f"{return_type} {method.name}({params})"

    def _compare_declarations(
        self, l1_decls: Dict[str, Any], l2_decls: Dict[str, Any], library_name: str
    ) -> List[Dict[str, Any]]:
        """Compare L1 and L2 declarations to find breaking changes."""
        breaking_changes = []

        # Build maps for comparison
        l1_methods = {
            f"{m['package']}.{m['class']}.{m['name']}": m for m in l1_decls.get("methods", [])
        }
        l2_methods = {
            f"{m['package']}.{m['class']}.{m['name']}": m for m in l2_decls.get("methods", [])
        }

        # Find removed methods
        for method_key, l1_method in l1_methods.items():
            if method_key not in l2_methods:
                breaking_changes.append(
                    {
                        "id": f"bc_{len(breaking_changes) + 1:03d}",
                        "class": f"{l1_method['package']}.{l1_method['class']}",
                        "method": l1_method["name"],
                        "change_type": "method_removed",
                        "old_signature": l1_method["signature"],
                        "new_signature": None,
                        "change_description": f"Method {l1_method['name']} was removed in {library_name}",
                    }
                )

        # Find changed signatures
        for method_key, l1_method in l1_methods.items():
            if method_key in l2_methods:
                l2_method = l2_methods[method_key]
                if l1_method["signature"] != l2_method["signature"]:
                    breaking_changes.append(
                        {
                            "id": f"bc_{len(breaking_changes) + 1:03d}",
                            "class": f"{l1_method['package']}.{l1_method['class']}",
                            "method": l1_method["name"],
                            "change_type": "signature_changed",
                            "old_signature": l1_method["signature"],
                            "new_signature": l2_method["signature"],
                            "change_description": f"Method signature changed: {l1_method['signature']} → {l2_method['signature']}",
                        }
                    )

        return breaking_changes

    def _add_source_context(
        self,
        breaking_changes: List[Dict[str, Any]],
        source_invocations: List[Dict[str, Any]],
        source_path: Path,
    ) -> List[Dict[str, Any]]:
        """Add source code context to breaking changes."""
        for breaking_change in breaking_changes:
            affected_locations = []

            # Find source code locations that use this method
            for inv in source_invocations:
                if self._matches_breaking_change(inv, breaking_change):
                    # Get source context
                    source_context = self._get_source_context(
                        source_path / inv["file_path"], inv["line_number"]
                    )

                    affected_locations.append(
                        {
                            "file": inv["file_path"],
                            "line": inv["line_number"],
                            "column": inv.get("column_number"),
                            "source_context": source_context,
                        }
                    )

            breaking_change["affected_locations"] = affected_locations

        return breaking_changes

    def _matches_breaking_change(
        self, invocation: Dict[str, Any], breaking_change: Dict[str, Any]
    ) -> bool:
        """Check if invocation matches breaking change."""
        # Simple matching: check if method name matches
        # In production, you'd need more sophisticated matching
        return invocation.get("callee_member") == breaking_change["method"] or breaking_change[
            "method"
        ] in invocation.get("callee_member", "")

    def _get_source_context(
        self, file_path: Path, line_number: int, context_lines: int = 5
    ) -> Dict[str, Any]:
        """Get source code context around a specific line."""
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()

            # Get target line
            target_line = lines[line_number - 1] if line_number <= len(lines) else ""

            # Get surrounding context
            start = max(0, line_number - context_lines - 1)
            end = min(len(lines), line_number + context_lines)
            surrounding = "\n".join(lines[start:end])

            # Get full method (simplified - would need AST parsing for accurate method extraction)
            full_method = self._extract_method(lines, line_number)

            # Get class name and imports (simplified)
            class_name = self._extract_class_name(lines)
            imports = self._extract_imports(lines)

            return {
                "target_line": target_line,
                "surrounding_context": surrounding,
                "full_method": full_method,
                "class_name": class_name,
                "package": self._extract_package(lines),
                "imports": imports,
            }

        except Exception as e:
            logger.warning(f"⚠️ Failed to get source context: {e}")
            return {
                "target_line": "",
                "surrounding_context": "",
                "full_method": "",
                "class_name": "",
                "package": None,
                "imports": [],
            }

    def _extract_method(self, lines: List[str], line_number: int) -> str:
        """Extract full method containing the line (simplified)."""
        # This is a simplified extraction - in production, use AST parsing
        start = max(0, line_number - 10)
        end = min(len(lines), line_number + 10)
        return "\n".join(lines[start:end])

    def _extract_class_name(self, lines: List[str]) -> str:
        """Extract class name from file (simplified)."""
        for line in lines:
            if "class " in line:
                parts = line.split("class ")
                if len(parts) > 1:
                    return parts[1].split()[0].split("{")[0]
        return ""

    def _extract_package(self, lines: List[str]) -> Optional[str]:
        """Extract package name from file."""
        for line in lines:
            if line.strip().startswith("package "):
                return line.strip().replace("package ", "").replace(";", "")
        return None

    def _extract_imports(self, lines: List[str]) -> List[str]:
        """Extract import statements from file."""
        imports = []
        for line in lines:
            if line.strip().startswith("import "):
                imports.append(line.strip())
        return imports

    def _generate_summary(self, breaking_changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics."""
        affected_files = set()
        affected_invocations = 0
        unique_classes = set()

        for bc in breaking_changes:
            unique_classes.add(bc["class"])
            for location in bc.get("affected_locations", []):
                affected_files.add(location["file"])
                affected_invocations += 1

        return {
            "breaking_changes_count": len(breaking_changes),
            "affected_files": len(affected_files),
            "affected_invocations": affected_invocations,
            "unique_classes_changed": len(unique_classes),
            "unique_methods_changed": len(breaking_changes),
        }

    def _resolve_library_github_url(self, library_name: str) -> Optional[str]:
        """Resolve library name to GitHub URL."""
        # Known library mappings
        known_libraries = {
            "spring-boot": "https://github.com/spring-projects/spring-boot.git",
            "log4j": "https://github.com/apache/logging-log4j2.git",
            "hibernate": "https://github.com/hibernate/hibernate-orm.git",
            "jackson": "https://github.com/FasterXML/jackson-databind.git",
            "jackson-databind": "https://github.com/FasterXML/jackson-databind.git",
            "jackson-core": "https://github.com/FasterXML/jackson-core.git",
            "jackson-annotations": "https://github.com/FasterXML/jackson-annotations.git",
        }

        return known_libraries.get(library_name.lower())
