"""
Java code transformer for applying breaking change fixes.

This service generates actual code transformations based on breaking changes
detected during library migration analysis. It produces unified diffs that
can be applied to source files.

Supported transformation types:
- Method renames
- Signature changes (parameter additions/removals/type changes)
- Method removals (with suggested alternatives)
- Import updates
- Type migrations
"""

import difflib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CodeFix:
    """Represents a single code fix to apply."""

    file_path: str
    line_number: int
    original_line: str
    fixed_line: str
    change_type: str
    description: str
    breaking_change_id: str
    confidence: float  # 0.0 - 1.0


@dataclass
class JavaFileDiff:
    """Represents a diff for a single Java file."""

    file_path: str
    original_content: str
    modified_content: str
    diff_text: str
    lines_added: int
    lines_removed: int
    fixes_applied: List[CodeFix]


class JavaCodeTransformer:
    """
    Transform Java source code to fix breaking changes from library upgrades.

    This class analyzes breaking changes and generates actual code fixes,
    not just TODOs or suggestions. It handles common migration patterns.
    """

    # Known migration patterns for common libraries
    MIGRATION_PATTERNS = {
        # Jackson patterns
        "jackson": {
            "ObjectMapper.readValue": {
                "signature_changed": {
                    # Pattern: (String, Class<T>) -> (String, TypeReference<T>) for generics
                    "patterns": [
                        (
                            r"\.readValue\(([^,]+),\s*([A-Z][a-zA-Z0-9<>]+)\.class\)",
                            r".readValue(\1, new TypeReference<\2>(){})",
                        ),
                    ],
                    "imports_needed": ["com.fasterxml.jackson.core.type.TypeReference"],
                }
            },
            "JsonNode.get": {
                "method_removed": {
                    "replacement": "path",
                    "note": "get() returns null for missing, path() returns MissingNode",
                }
            },
            # Deprecated enableDefaultTyping removed in 2.10+
            "ObjectMapper.enableDefaultTyping": {
                "method_removed": {
                    "replacement": "activateDefaultTyping",
                    "transform": lambda m: m.replace(
                        "enableDefaultTyping", "activateDefaultTyping"
                    ),
                }
            },
        },
        # Spring patterns
        "spring": {
            "WebSecurityConfigurerAdapter": {
                "class_removed": {
                    "note": "Use SecurityFilterChain bean instead",
                    "migration_guide": "https://spring.io/blog/2022/02/21/spring-security-without-the-websecurityconfigureradapter",
                }
            },
        },
        # Log4j patterns
        "log4j": {
            "Logger.getLogger": {
                "method_removed": {
                    "replacement": "LogManager.getLogger",
                    "imports_needed": ["org.apache.logging.log4j.LogManager"],
                }
            },
        },
    }

    def __init__(self):
        """Initialize the transformer."""
        self.fixes_applied = []

    def generate_code_fixes(
        self,
        breaking_changes: List[Dict[str, Any]],
        source_files: Dict[str, str],
        library_name: str,
    ) -> Dict[str, JavaFileDiff]:
        """
        Generate code fixes for all breaking changes.

        Args:
            breaking_changes: List of breaking changes with affected_locations
            source_files: Dict of {file_path: file_content}
            library_name: Name of the library being upgraded

        Returns:
            Dict of {file_path: JavaFileDiff} with all fixes applied
        """
        logger.info(f"🔧 Generating fixes for {len(breaking_changes)} breaking changes")

        file_diffs = {}
        fixes_by_file: Dict[str, List[CodeFix]] = {}

        # Collect all fixes per file
        for bc in breaking_changes:
            for location in bc.get("affected_locations", []):
                file_path = location["file"]

                if file_path not in source_files:
                    logger.warning(f"⚠️ Source file not found: {file_path}")
                    continue

                fix = self._generate_fix_for_location(
                    bc, location, source_files[file_path], library_name
                )

                if fix:
                    if file_path not in fixes_by_file:
                        fixes_by_file[file_path] = []
                    fixes_by_file[file_path].append(fix)

        # Apply fixes to each file
        for file_path, fixes in fixes_by_file.items():
            original_content = source_files[file_path]
            modified_content, applied_fixes = self._apply_fixes(original_content, fixes)

            # Generate unified diff
            diff_text = self._create_unified_diff(original_content, modified_content, file_path)

            lines_added = diff_text.count("\n+") - 1  # Exclude +++ line
            lines_removed = diff_text.count("\n-") - 1  # Exclude --- line

            file_diffs[file_path] = JavaFileDiff(
                file_path=file_path,
                original_content=original_content,
                modified_content=modified_content,
                diff_text=diff_text,
                lines_added=max(0, lines_added),
                lines_removed=max(0, lines_removed),
                fixes_applied=applied_fixes,
            )

            logger.info(f"✅ Generated diff for {file_path}: {len(applied_fixes)} fixes")

        return file_diffs

    def _generate_fix_for_location(
        self,
        breaking_change: Dict[str, Any],
        location: Dict[str, Any],
        file_content: str,
        library_name: str,
    ) -> Optional[CodeFix]:
        """Generate a fix for a specific breaking change location."""
        change_type = breaking_change.get("change_type", "")
        method_name = breaking_change.get("method", "")
        class_name = breaking_change.get("class", "")
        old_sig = breaking_change.get("old_signature", "")
        new_sig = breaking_change.get("new_signature", "")

        line_number = location.get("line", 0)
        source_context = location.get("source_context", {})
        target_line = source_context.get("target_line", "")

        if not target_line or line_number <= 0:
            # Try to get the line from file content
            lines = file_content.splitlines()
            if 0 < line_number <= len(lines):
                target_line = lines[line_number - 1]
            else:
                return None

        # Determine fix based on change type
        fixed_line = target_line
        description = ""
        confidence = 0.5  # Default confidence

        if change_type == "method_removed":
            fixed_line, description, confidence = self._fix_method_removed(
                target_line, method_name, class_name, library_name, breaking_change
            )
        elif change_type == "signature_changed":
            fixed_line, description, confidence = self._fix_signature_changed(
                target_line, method_name, old_sig, new_sig, library_name
            )
        elif change_type == "method_renamed":
            new_method = breaking_change.get("new_method", "")
            fixed_line, description, confidence = self._fix_method_renamed(
                target_line, method_name, new_method
            )
        elif change_type == "parameter_added":
            fixed_line, description, confidence = self._fix_parameter_added(
                target_line, method_name, new_sig, breaking_change
            )
        elif change_type == "return_type_changed":
            fixed_line, description, confidence = self._fix_return_type_changed(
                target_line, method_name, old_sig, new_sig
            )
        else:
            # Generic fix: add TODO comment
            fixed_line = f"{target_line}  // TODO: Update for {library_name} upgrade - {breaking_change.get('change_description', 'breaking change')}"
            description = f"Added TODO for unhandled change type: {change_type}"
            confidence = 0.3

        if fixed_line == target_line:
            return None  # No change needed

        return CodeFix(
            file_path=location["file"],
            line_number=line_number,
            original_line=target_line,
            fixed_line=fixed_line,
            change_type=change_type,
            description=description,
            breaking_change_id=breaking_change.get("id", "unknown"),
            confidence=confidence,
        )

    def _fix_method_removed(
        self,
        line: str,
        method_name: str,
        class_name: str,
        library_name: str,
        breaking_change: Dict[str, Any],
    ) -> Tuple[str, str, float]:
        """Fix a removed method by suggesting or applying replacement."""
        # Check for known migration patterns
        lib_patterns = self.MIGRATION_PATTERNS.get(library_name.lower(), {})
        method_patterns = lib_patterns.get(method_name, {})

        if "method_removed" in method_patterns:
            pattern_info = method_patterns["method_removed"]
            replacement = pattern_info.get("replacement")

            if replacement:
                # Apply the replacement
                fixed_line = line.replace(f".{method_name}(", f".{replacement}(")
                return (
                    fixed_line,
                    f"Replaced removed method '{method_name}' with '{replacement}'",
                    0.9,
                )

            if "transform" in pattern_info:
                fixed_line = pattern_info["transform"](line)
                return (fixed_line, f"Applied migration transform for '{method_name}'", 0.85)

        # No known pattern - add commented replacement suggestion
        alternative = breaking_change.get("suggested_alternative", "")
        if alternative:
            fixed_line = (
                f"// FIXME: Method '{method_name}' removed. Use: {alternative}\n        {line}"
            )
        else:
            fixed_line = f"// FIXME: Method '{method_name}' was removed in library upgrade. Find alternative.\n        {line}"

        return (fixed_line, f"Marked removed method '{method_name}' with FIXME", 0.5)

    def _fix_signature_changed(
        self,
        line: str,
        method_name: str,
        old_sig: str,
        new_sig: str,
        library_name: str,
    ) -> Tuple[str, str, float]:
        """Fix a method with changed signature."""
        # Parse old and new signatures to understand the change
        old_params = self._parse_signature_params(old_sig)
        new_params = self._parse_signature_params(new_sig)

        # Determine what changed
        if len(new_params) > len(old_params):
            # Parameter added - add default value
            added_params = len(new_params) - len(old_params)

            # Find the method call and add default arguments
            pattern = rf"\.{re.escape(method_name)}\(([^)]*)\)"
            match = re.search(pattern, line)

            if match:
                existing_args = match.group(1)
                # Add null/default for new parameters
                new_args = existing_args
                for i in range(added_params):
                    new_param = new_params[len(old_params) + i]
                    default_val = self._get_default_value(new_param.get("type", "Object"))
                    new_args += f", {default_val}"

                fixed_line = re.sub(pattern, f".{method_name}({new_args})", line)
                return (
                    fixed_line,
                    f"Added {added_params} new parameter(s) to '{method_name}' call",
                    0.8,
                )

        elif len(new_params) < len(old_params):
            # Parameter removed - remove argument
            removed_count = len(old_params) - len(new_params)

            # Add comment about removed parameters
            fixed_line = (
                f"// Note: {removed_count} parameter(s) removed from {method_name}\n        {line}"
            )
            return (fixed_line, f"Noted removed parameters from '{method_name}'", 0.6)

        else:
            # Parameter type changed
            # Check for known type migrations
            fixed_line = line
            for i, (old_p, new_p) in enumerate(zip(old_params, new_params)):
                if old_p.get("type") != new_p.get("type"):
                    # Add cast or conversion hint
                    old_type = old_p.get("type", "?")
                    new_type = new_p.get("type", "?")
                    fixed_line = f"// Note: Parameter {i + 1} type changed from {old_type} to {new_type}\n        {line}"
                    return (fixed_line, f"Noted parameter type change in '{method_name}'", 0.6)

        # Check for known library patterns
        lib_patterns = self.MIGRATION_PATTERNS.get(library_name.lower(), {})
        if method_name in lib_patterns and "signature_changed" in lib_patterns[method_name]:
            pattern_info = lib_patterns[method_name]["signature_changed"]
            for old_pattern, replacement in pattern_info.get("patterns", []):
                if re.search(old_pattern, line):
                    fixed_line = re.sub(old_pattern, replacement, line)
                    return (fixed_line, f"Applied known migration pattern for '{method_name}'", 0.9)

        # Generic fix - add comment
        fixed_line = f"// TODO: Update call to {method_name} - signature changed from {old_sig} to {new_sig}\n        {line}"
        return (fixed_line, f"Added TODO for signature change in '{method_name}'", 0.5)

    def _fix_method_renamed(
        self,
        line: str,
        old_method: str,
        new_method: str,
    ) -> Tuple[str, str, float]:
        """Fix a renamed method."""
        if not new_method:
            fixed_line = (
                f"// TODO: Method '{old_method}' was renamed. Find new name.\n        {line}"
            )
            return (fixed_line, f"Added TODO for renamed method '{old_method}'", 0.4)

        # Simple replacement
        pattern = rf"\.{re.escape(old_method)}\("
        if re.search(pattern, line):
            fixed_line = re.sub(pattern, f".{new_method}(", line)
            return (fixed_line, f"Renamed method call from '{old_method}' to '{new_method}'", 0.95)

        return (line, "", 0.0)

    def _fix_parameter_added(
        self,
        line: str,
        method_name: str,
        new_sig: str,
        breaking_change: Dict[str, Any],
    ) -> Tuple[str, str, float]:
        """Fix a method call where a new parameter was added."""
        new_params = self._parse_signature_params(new_sig)

        # Find the method call
        pattern = rf"\.{re.escape(method_name)}\(([^)]*)\)"
        match = re.search(pattern, line)

        if match:
            existing_args = match.group(1)
            existing_count = (
                len([a for a in existing_args.split(",") if a.strip()])
                if existing_args.strip()
                else 0
            )

            # Add default values for missing parameters
            missing_count = len(new_params) - existing_count
            if missing_count > 0:
                new_args = existing_args
                for i in range(missing_count):
                    param_idx = existing_count + i
                    if param_idx < len(new_params):
                        param_type = new_params[param_idx].get("type", "Object")
                        default_val = self._get_default_value(param_type)
                        if new_args.strip():
                            new_args += f", {default_val}"
                        else:
                            new_args = default_val

                fixed_line = re.sub(pattern, f".{method_name}({new_args})", line)
                return (
                    fixed_line,
                    f"Added {missing_count} default parameter(s) to '{method_name}' call",
                    0.75,
                )

        return (line, "", 0.0)

    def _fix_return_type_changed(
        self,
        line: str,
        method_name: str,
        old_sig: str,
        new_sig: str,
    ) -> Tuple[str, str, float]:
        """Fix code where return type of a method changed."""
        old_return = old_sig.split()[0] if old_sig else "?"
        new_return = new_sig.split()[0] if new_sig else "?"

        # Add cast if needed
        if old_return != new_return:
            fixed_line = f"// Note: {method_name} now returns {new_return} instead of {old_return}\n        {line}"
            return (fixed_line, f"Noted return type change for '{method_name}'", 0.6)

        return (line, "", 0.0)

    def _parse_signature_params(self, signature: str) -> List[Dict[str, str]]:
        """Parse method signature to extract parameters."""
        params = []

        # Extract parameters from signature like "void method(String arg1, int arg2)"
        match = re.search(r"\(([^)]*)\)", signature)
        if match:
            param_str = match.group(1)
            if param_str.strip():
                for param in param_str.split(","):
                    param = param.strip()
                    parts = param.rsplit(" ", 1)
                    if len(parts) == 2:
                        params.append({"type": parts[0], "name": parts[1]})
                    else:
                        params.append({"type": param, "name": ""})

        return params

    def _get_default_value(self, java_type: str) -> str:
        """Get a default value for a Java type."""
        type_lower = java_type.lower()

        if type_lower in ("int", "integer"):
            return "0"
        elif type_lower in ("long"):
            return "0L"
        elif type_lower in ("double"):
            return "0.0"
        elif type_lower in ("float"):
            return "0.0f"
        elif type_lower in ("boolean"):
            return "false"
        elif type_lower in ("char", "character"):
            return "'\\0'"
        elif type_lower in ("byte"):
            return "(byte)0"
        elif type_lower in ("short"):
            return "(short)0"
        elif "string" in type_lower:
            return '""'
        elif "list" in type_lower or "collection" in type_lower:
            return "Collections.emptyList()"
        elif "map" in type_lower:
            return "Collections.emptyMap()"
        elif "set" in type_lower:
            return "Collections.emptySet()"
        elif "optional" in type_lower:
            return "Optional.empty()"
        else:
            return "null"

    def _apply_fixes(
        self,
        content: str,
        fixes: List[CodeFix],
    ) -> Tuple[str, List[CodeFix]]:
        """Apply all fixes to file content."""
        lines = content.splitlines(keepends=True)
        applied_fixes = []

        # Sort fixes by line number in reverse order to avoid offset issues
        sorted_fixes = sorted(fixes, key=lambda f: f.line_number, reverse=True)

        for fix in sorted_fixes:
            line_idx = fix.line_number - 1

            if 0 <= line_idx < len(lines):
                original = lines[line_idx].rstrip("\n\r")

                # Verify the original line matches what we expect
                if original.strip() == fix.original_line.strip():
                    # Preserve original indentation
                    indent = len(original) - len(original.lstrip())
                    indent_str = original[:indent]

                    # Handle multi-line fixes (comments + code)
                    if "\n" in fix.fixed_line:
                        fix_lines = fix.fixed_line.split("\n")
                        fixed_with_indent = "\n".join(
                            indent_str + fl.lstrip() if fl.strip() else fl for fl in fix_lines
                        )
                        lines[line_idx] = fixed_with_indent + "\n"
                    else:
                        lines[line_idx] = indent_str + fix.fixed_line.lstrip() + "\n"

                    applied_fixes.append(fix)
                else:
                    logger.warning(
                        f"⚠️ Line mismatch at {fix.file_path}:{fix.line_number}. "
                        f"Expected: '{fix.original_line.strip()}', "
                        f"Found: '{original.strip()}'"
                    )

        return "".join(lines), applied_fixes

    def _create_unified_diff(
        self,
        original: str,
        modified: str,
        file_path: str,
    ) -> str:
        """Create a unified diff between original and modified content."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )

        return "".join(diff)

    def generate_import_updates(
        self,
        breaking_changes: List[Dict[str, Any]],
        file_content: str,
        library_name: str,
    ) -> List[str]:
        """Generate import statements that need to be added."""
        imports_needed = set()

        lib_patterns = self.MIGRATION_PATTERNS.get(library_name.lower(), {})

        for bc in breaking_changes:
            method_name = bc.get("method", "")
            change_type = bc.get("change_type", "")

            if method_name in lib_patterns and change_type in lib_patterns[method_name]:
                pattern_info = lib_patterns[method_name][change_type]
                for imp in pattern_info.get("imports_needed", []):
                    imports_needed.add(imp)

        # Filter out imports that already exist
        existing_imports = set(re.findall(r"^import\s+([^;]+);", file_content, re.MULTILINE))

        return [imp for imp in imports_needed if imp not in existing_imports]
