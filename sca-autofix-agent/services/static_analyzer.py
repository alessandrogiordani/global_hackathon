"""
Static code analyzer for detecting package usage and method calls.
Uses Python AST (Abstract Syntax Tree) parsing to analyze source code.
"""

import ast
import logging
from pathlib import Path
from typing import Optional
from collections import defaultdict

from databricks.sdk import WorkspaceClient
from models.usage import (
    ImportStatement,
    MethodUsage,
    PackageUsageAnalysis,
)


logger = logging.getLogger(__name__)


class StaticAnalyzer:
    """Analyzes Python source code to detect package usage and method calls."""

    def __init__(self, workspace_client: WorkspaceClient):
        """Initialize the static analyzer with Databricks workspace client."""
        self.w = workspace_client

    def analyze_package_usage(
        self, repo_path: str, package_name: str, package_version: str
    ) -> PackageUsageAnalysis:
        """
        Analyze how a specific package is used throughout the repository.

        Args:
            repo_path: Path to the repository in Databricks workspace
            package_name: Name of the package to analyze
            package_version: Current version of the package

        Returns:
            PackageUsageAnalysis containing all imports and method usages
        """
        logger.info(f"🔍 Analyzing usage of {package_name} in {repo_path}")

        imports = []
        method_usages = []
        files_with_package = set()

        # Find all Python files in the repo
        python_files = self._find_python_files(repo_path)
        logger.info(f"📁 Found {len(python_files)} Python files to analyze")

        for file_path in python_files:
            try:
                # Read file content
                content = self.w.workspace.download(file_path).read().decode("utf-8")

                # Parse and analyze
                file_imports, file_usages = self._analyze_file(file_path, content, package_name)

                if file_imports:
                    imports.extend(file_imports)
                    files_with_package.add(file_path)

                if file_usages:
                    method_usages.extend(file_usages)

            except Exception as e:
                logger.warning(f"⚠️ Failed to analyze {file_path}: {e}")
                continue

        # Extract unique methods used
        unique_methods = sorted(set(usage.method_name for usage in method_usages))

        logger.info(
            f"✅ Found {len(imports)} imports and {len(method_usages)} method usages across {len(files_with_package)} files"
        )

        return PackageUsageAnalysis(
            package_name=package_name,
            package_version=package_version,
            imports=imports,
            method_usages=method_usages,
            total_files=len(files_with_package),
            total_usages=len(method_usages),
            unique_methods=unique_methods,
        )

    def _find_python_files(self, repo_path: str) -> list[str]:
        """Recursively find all Python files in the repository."""
        python_files = []

        try:
            items = list(self.w.workspace.list(repo_path, recursive=True))
            for item in items:
                if item.path and item.path.endswith(".py"):
                    python_files.append(item.path)
        except Exception as e:
            logger.error(f"❌ Failed to list files in {repo_path}: {e}")

        return python_files

    def _analyze_file(
        self, file_path: str, content: str, target_package: str
    ) -> tuple[list[ImportStatement], list[MethodUsage]]:
        """
        Analyze a single Python file for imports and usage of target package.

        Returns:
            Tuple of (imports, method_usages)
        """
        imports = []
        method_usages = []

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            logger.warning(f"⚠️ Syntax error in {file_path}: {e}")
            return imports, method_usages

        # Track aliases for the package (e.g., 'import pandas as pd')
        package_aliases = {}

        # First pass: collect imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if self._matches_package(alias.name, target_package):
                        imports.append(
                            ImportStatement(
                                file_path=file_path,
                                line_number=node.lineno,
                                package_name=alias.name,
                                imported_items=[],
                                alias=alias.asname,
                                import_type="module",
                            )
                        )
                        # Track alias for usage detection
                        package_aliases[alias.asname or alias.name] = alias.name

            elif isinstance(node, ast.ImportFrom):
                if node.module and self._matches_package(node.module, target_package):
                    imported_items = [alias.name for alias in node.names]
                    imports.append(
                        ImportStatement(
                            file_path=file_path,
                            line_number=node.lineno,
                            package_name=node.module,
                            imported_items=imported_items,
                            alias=None,
                            import_type="from" if "*" not in imported_items else "star",
                        )
                    )
                    # Track imported items
                    for alias in node.names:
                        package_aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"

        # Second pass: find method usages if package is imported
        if package_aliases:
            method_usages = self._find_method_usages(
                tree, file_path, content, target_package, package_aliases
            )

        return imports, method_usages

    def _find_method_usages(
        self,
        tree: ast.AST,
        file_path: str,
        content: str,
        target_package: str,
        package_aliases: dict[str, str],
    ) -> list[MethodUsage]:
        """Find all method/function calls related to the target package."""
        method_usages = []
        lines = content.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Extract the function/method being called
                call_info = self._extract_call_info(node, package_aliases)

                if call_info:
                    method_name, package_prefix = call_info

                    # Get context (few lines around the call)
                    context = self._get_context(lines, node.lineno, context_lines=2)

                    # Try to reconstruct call signature
                    call_signature = self._reconstruct_call(node)

                    method_usages.append(
                        MethodUsage(
                            package_name=package_prefix,
                            method_name=method_name,
                            file_path=file_path,
                            line_number=node.lineno,
                            context=context,
                            call_signature=call_signature,
                        )
                    )

        return method_usages

    def _extract_call_info(
        self, node: ast.Call, package_aliases: dict[str, str]
    ) -> Optional[tuple[str, str]]:
        """
        Extract method name and package from a Call node.

        Returns:
            Tuple of (method_name, package_name) or None
        """
        func = node.func

        if isinstance(func, ast.Attribute):
            # e.g., pd.DataFrame() or obj.method()
            parts = []
            current = func

            while isinstance(current, ast.Attribute):
                parts.insert(0, current.attr)
                current = current.value

            if isinstance(current, ast.Name):
                parts.insert(0, current.id)

            # Check if the base is a known package alias
            if parts and parts[0] in package_aliases:
                package_name = package_aliases[parts[0]]
                method_name = ".".join(parts[1:]) if len(parts) > 1 else parts[0]
                return method_name, package_name

        elif isinstance(func, ast.Name):
            # Direct function call, e.g., DataFrame()
            if func.id in package_aliases:
                return func.id, package_aliases[func.id]

        return None

    def _matches_package(self, module_name: str, target_package: str) -> bool:
        """Check if a module name matches or is a submodule of target package."""
        return module_name == target_package or module_name.startswith(target_package + ".")

    def _get_context(self, lines: list[str], line_number: int, context_lines: int = 2) -> str:
        """Get a few lines of context around the target line."""
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)
        context_snippet = lines[start:end]
        return "\n".join(context_snippet)

    def _reconstruct_call(self, node: ast.Call) -> str:
        """Attempt to reconstruct the call signature from AST node."""
        try:
            # This is a simplified reconstruction
            func_name = ast.unparse(node.func)
            args = [ast.unparse(arg) for arg in node.args]
            kwargs = [f"{kw.arg}={ast.unparse(kw.value)}" for kw in node.keywords]
            all_args = args + kwargs
            return f"{func_name}({', '.join(all_args)})"
        except Exception:
            return "Unknown"
