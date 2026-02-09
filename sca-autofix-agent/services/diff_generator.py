"""
Diff generator service for creating patch previews.

This module handles two types of diffs:
1. Manifest file updates (requirements.txt, pom.xml, package.json)
2. Java source code transformations for breaking API changes
"""

import difflib
import logging
import re
from typing import Dict, List, Optional, Any

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from models import FileDiff, PatchPreview, UpgradePlan
from services.java_code_transformer import JavaCodeTransformer, JavaFileDiff, CodeFix

logger = logging.getLogger(__name__)


class DiffGenerator:
    """Generates visual diffs for proposed package upgrades."""

    def generate_patch_preview(
        self,
        repo_path: str,
        upgrade_plan: UpgradePlan,
        file_contents: dict[str, str],
    ) -> PatchPreview:
        """
        Generate a preview of proposed changes.

        Args:
            repo_path: Path to the repository
            upgrade_plan: The upgrade plan to preview
            file_contents: Dict of {file_path: current_content}

        Returns:
            PatchPreview with diffs and visualizations
        """
        file_diffs = []
        files_to_modify = list(file_contents.keys())

        for file_path, original_content in file_contents.items():
            # Generate modified content based on upgrade plan
            modified_content = self._apply_upgrades_to_content(
                original_content, upgrade_plan, file_path
            )

            # Create diff
            diff = self._create_unified_diff(original_content, modified_content, file_path)

            # Count changes
            lines_added = diff.count("\n+")
            lines_removed = diff.count("\n-")

            file_diff = FileDiff(
                file_path=file_path,
                diff_text=diff,
                lines_added=lines_added,
                lines_removed=lines_removed,
            )
            file_diffs.append(file_diff)

        # Generate HTML visualization
        visual_diff_html = self._generate_html_diff(file_diffs)

        # Calculate impact summary
        total_changes = sum(fd.lines_added + fd.lines_removed for fd in file_diffs)
        breaking_changes = sum(1 for rec in upgrade_plan.recommendations if rec.is_breaking_change)

        impact_summary = {
            "total_changes": total_changes,
            "breaking_changes": breaking_changes,
            "files_modified": len(files_to_modify),
        }

        return PatchPreview(
            repo_path=repo_path,
            upgrade_plan=upgrade_plan,
            files_to_modify=files_to_modify,
            file_diffs=file_diffs,
            visual_diff_html=visual_diff_html,
            impact_summary=impact_summary,
        )

    def _apply_upgrades_to_content(
        self, content: str, upgrade_plan: UpgradePlan, file_path: str
    ) -> str:
        """
        Apply package upgrades to file content.

        Args:
            content: Original file content
            upgrade_plan: Upgrade plan with recommendations
            file_path: Path to the file being modified

        Returns:
            Modified content with upgraded versions
        """
        modified = content

        for recommendation in upgrade_plan.recommendations:
            package = recommendation.package
            from_ver = recommendation.from_version
            to_ver = recommendation.to_version

            # Handle different file types
            if file_path.endswith("requirements.txt"):
                # Format: package==1.0.0
                pattern = rf"^{re.escape(package)}==[\d.]+$"
                replacement = f"{package}=={to_ver}"
                modified = re.sub(pattern, replacement, modified, flags=re.MULTILINE)

            elif file_path.endswith("pyproject.toml"):
                # Format: package = "^1.0.0" or "package>=1.0.0"
                pattern = rf'"{re.escape(package)}[><=~^]+[\d.]+"'
                replacement = f'"{package}=={to_ver}"'
                modified = re.sub(pattern, replacement, modified)

            elif file_path.endswith("package.json"):
                # Format: "package": "^1.0.0"
                pattern = rf'"{re.escape(package)}":\s*"[^"]*"'
                replacement = f'"{package}": "^{to_ver}"'
                modified = re.sub(pattern, replacement, modified)

        return modified

    def _create_unified_diff(self, original: str, modified: str, file_path: str) -> str:
        """
        Create a unified diff between original and modified content.

        Args:
            original: Original file content
            modified: Modified file content
            file_path: Path to the file

        Returns:
            Unified diff string
        """
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

    def _generate_html_diff(self, file_diffs: list[FileDiff]) -> str:
        """
        Generate HTML visualization of diffs with syntax highlighting.

        Args:
            file_diffs: List of file diffs

        Returns:
            HTML string with styled diffs
        """
        html_parts = [
            """
            <html>
            <head>
                <style>
                    body { font-family: monospace; background: #f5f5f5; padding: 20px; }
                    .file-diff { background: white; margin-bottom: 20px; border: 1px solid #ddd; border-radius: 5px; }
                    .file-header { background: #f0f0f0; padding: 10px; font-weight: bold; border-bottom: 1px solid #ddd; }
                    .diff-content { padding: 10px; }
                    .diff-line { padding: 2px 5px; }
                    .added { background: #e6ffed; color: #22863a; }
                    .removed { background: #ffeef0; color: #b31d28; }
                    .context { background: white; color: #24292e; }
                    .stats { color: #666; font-size: 0.9em; }
                </style>
            </head>
            <body>
            """
        ]

        for file_diff in file_diffs:
            html_parts.append(f'<div class="file-diff">')
            html_parts.append(
                f'<div class="file-header">'
                f"{file_diff.file_path} "
                f'<span class="stats">'
                f"(+{file_diff.lines_added} -{file_diff.lines_removed})"
                f"</span>"
                f"</div>"
            )
            html_parts.append('<div class="diff-content"><pre>')

            # Color code diff lines
            for line in file_diff.diff_text.split("\n"):
                if line.startswith("+") and not line.startswith("+++"):
                    html_parts.append(
                        f'<div class="diff-line added">{self._escape_html(line)}</div>'
                    )
                elif line.startswith("-") and not line.startswith("---"):
                    html_parts.append(
                        f'<div class="diff-line removed">{self._escape_html(line)}</div>'
                    )
                elif line.startswith("@@"):
                    html_parts.append(
                        f'<div class="diff-line context" style="color: #0969da;">{self._escape_html(line)}</div>'
                    )
                else:
                    html_parts.append(
                        f'<div class="diff-line context">{self._escape_html(line)}</div>'
                    )

            html_parts.append("</pre></div>")
            html_parts.append("</div>")

        html_parts.append("</body></html>")

        return "".join(html_parts)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def generate_java_migration_diff(
        self,
        breaking_changes: List[Dict[str, Any]],
        source_files: Dict[str, str],
        library_name: str,
        current_version: str,
        target_version: str,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive diffs for Java source code migration.

        This method uses the JavaCodeTransformer to generate actual code fixes
        for breaking changes detected during library migration analysis.

        Args:
            breaking_changes: List of breaking changes with affected_locations
            source_files: Dict of {file_path: file_content}
            library_name: Name of the library being upgraded
            current_version: Current library version
            target_version: Target library version

        Returns:
            dict: {
                "status": "success",
                "library": "jackson-databind",
                "from_version": "2.9.8",
                "to_version": "2.15.0",
                "file_diffs": [...],
                "summary": {...},
                "visual_diff_html": "<html>..."
            }
        """
        logger.info(
            f"🔧 Generating migration diff: {library_name} {current_version} → {target_version}"
        )

        try:
            # Use JavaCodeTransformer to generate fixes
            transformer = JavaCodeTransformer()
            java_diffs = transformer.generate_code_fixes(
                breaking_changes, source_files, library_name
            )

            # Convert to FileDiff format for visualization
            file_diffs = []
            all_fixes = []

            for file_path, java_diff in java_diffs.items():
                file_diff = FileDiff(
                    file_path=file_path,
                    diff_text=java_diff.diff_text,
                    lines_added=java_diff.lines_added,
                    lines_removed=java_diff.lines_removed,
                )
                file_diffs.append(file_diff)
                all_fixes.extend(java_diff.fixes_applied)

            # Generate HTML visualization
            visual_diff_html = self._generate_java_migration_html(
                java_diffs, library_name, current_version, target_version
            )

            # Calculate summary
            summary = self._calculate_migration_summary(all_fixes, java_diffs)

            logger.info(f"✅ Generated {len(file_diffs)} file diffs with {len(all_fixes)} fixes")

            return {
                "status": "success",
                "library": library_name,
                "from_version": current_version,
                "to_version": target_version,
                "file_diffs": [
                    {
                        "file_path": fd.file_path,
                        "diff_text": fd.diff_text,
                        "lines_added": fd.lines_added,
                        "lines_removed": fd.lines_removed,
                    }
                    for fd in file_diffs
                ],
                "fixes_applied": [
                    {
                        "file": fix.file_path,
                        "line": fix.line_number,
                        "change_type": fix.change_type,
                        "description": fix.description,
                        "confidence": fix.confidence,
                        "original": fix.original_line,
                        "fixed": fix.fixed_line,
                    }
                    for fix in all_fixes
                ],
                "summary": summary,
                "visual_diff_html": visual_diff_html,
            }

        except Exception as e:
            logger.error(f"❌ Failed to generate migration diff: {e}")
            return {
                "status": "error",
                "message": f"Failed to generate migration diff: {str(e)}",
                "library": library_name,
                "from_version": current_version,
                "to_version": target_version,
            }

    def _generate_java_migration_html(
        self,
        java_diffs: Dict[str, JavaFileDiff],
        library_name: str,
        current_version: str,
        target_version: str,
    ) -> str:
        """Generate HTML visualization for Java migration diffs."""
        html_parts = [
            f"""
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', sans-serif; background: #f5f5f5; padding: 20px; }}
                    .migration-header {{ 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 20px;
                        border-radius: 8px;
                        margin-bottom: 20px;
                    }}
                    .migration-header h1 {{ margin: 0 0 10px 0; }}
                    .migration-header .version {{ font-size: 1.2em; }}
                    .file-diff {{ 
                        background: white; 
                        margin-bottom: 20px; 
                        border: 1px solid #ddd; 
                        border-radius: 8px;
                        overflow: hidden;
                    }}
                    .file-header {{ 
                        background: #2d3748; 
                        color: white;
                        padding: 12px 16px; 
                        font-weight: bold;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }}
                    .file-header .path {{ font-family: monospace; }}
                    .stats {{ 
                        font-size: 0.85em;
                        display: flex;
                        gap: 10px;
                    }}
                    .stat-added {{ color: #68d391; }}
                    .stat-removed {{ color: #fc8181; }}
                    .diff-content {{ 
                        padding: 0; 
                        font-family: 'Fira Code', 'Consolas', monospace;
                        font-size: 13px;
                        line-height: 1.5;
                        overflow-x: auto;
                    }}
                    .diff-line {{ 
                        padding: 2px 16px;
                        white-space: pre;
                        border-left: 3px solid transparent;
                    }}
                    .added {{ 
                        background: #e6ffed; 
                        color: #22863a;
                        border-left-color: #22863a;
                    }}
                    .removed {{ 
                        background: #ffeef0; 
                        color: #b31d28;
                        border-left-color: #b31d28;
                    }}
                    .context {{ background: white; color: #24292e; }}
                    .line-marker {{ color: #6a737d; }}
                    .fix-info {{
                        background: #fffbdd;
                        border: 1px solid #f9c513;
                        border-radius: 4px;
                        padding: 10px 16px;
                        margin: 10px 16px;
                        font-size: 0.9em;
                    }}
                    .fix-info .confidence {{
                        display: inline-block;
                        padding: 2px 8px;
                        border-radius: 12px;
                        font-size: 0.8em;
                        margin-left: 10px;
                    }}
                    .confidence-high {{ background: #c6f6d5; color: #22543d; }}
                    .confidence-medium {{ background: #fefcbf; color: #744210; }}
                    .confidence-low {{ background: #fed7d7; color: #742a2a; }}
                </style>
            </head>
            <body>
            <div class="migration-header">
                <h1>🔄 Library Migration Diff</h1>
                <div class="version">
                    <strong>{library_name}</strong>: {current_version} → {target_version}
                </div>
            </div>
            """
        ]

        for file_path, java_diff in java_diffs.items():
            html_parts.append('<div class="file-diff">')
            html_parts.append(
                f'<div class="file-header">'
                f'<span class="path">📄 {file_path}</span>'
                f'<span class="stats">'
                f'<span class="stat-added">+{java_diff.lines_added}</span>'
                f'<span class="stat-removed">-{java_diff.lines_removed}</span>'
                f"</span>"
                f"</div>"
            )

            # Show fix summaries
            if java_diff.fixes_applied:
                for fix in java_diff.fixes_applied:
                    conf_class = (
                        "confidence-high"
                        if fix.confidence >= 0.8
                        else "confidence-medium"
                        if fix.confidence >= 0.5
                        else "confidence-low"
                    )
                    conf_pct = int(fix.confidence * 100)
                    html_parts.append(
                        f'<div class="fix-info">'
                        f"<strong>Line {fix.line_number}:</strong> {self._escape_html(fix.description)}"
                        f'<span class="confidence {conf_class}">{conf_pct}% confidence</span>'
                        f"</div>"
                    )

            html_parts.append('<div class="diff-content">')

            # Color code diff lines
            for line in java_diff.diff_text.split("\n"):
                if line.startswith("+") and not line.startswith("+++"):
                    html_parts.append(
                        f'<div class="diff-line added">{self._escape_html(line)}</div>'
                    )
                elif line.startswith("-") and not line.startswith("---"):
                    html_parts.append(
                        f'<div class="diff-line removed">{self._escape_html(line)}</div>'
                    )
                elif line.startswith("@@"):
                    html_parts.append(
                        f'<div class="diff-line context line-marker">{self._escape_html(line)}</div>'
                    )
                elif line.startswith("---") or line.startswith("+++"):
                    continue  # Skip file headers, we have our own
                else:
                    html_parts.append(
                        f'<div class="diff-line context">{self._escape_html(line)}</div>'
                    )

            html_parts.append("</div></div>")

        html_parts.append("</body></html>")

        return "".join(html_parts)

    def _calculate_migration_summary(
        self,
        fixes: List[CodeFix],
        java_diffs: Dict[str, JavaFileDiff],
    ) -> Dict[str, Any]:
        """Calculate summary statistics for migration."""
        # Count by change type
        change_types = {}
        for fix in fixes:
            ct = fix.change_type
            change_types[ct] = change_types.get(ct, 0) + 1

        # Calculate average confidence
        avg_confidence = sum(f.confidence for f in fixes) / len(fixes) if fixes else 0.0

        # Count by confidence level
        high_confidence = sum(1 for f in fixes if f.confidence >= 0.8)
        medium_confidence = sum(1 for f in fixes if 0.5 <= f.confidence < 0.8)
        low_confidence = sum(1 for f in fixes if f.confidence < 0.5)

        # Total lines changed
        total_added = sum(d.lines_added for d in java_diffs.values())
        total_removed = sum(d.lines_removed for d in java_diffs.values())

        return {
            "files_modified": len(java_diffs),
            "total_fixes": len(fixes),
            "lines_added": total_added,
            "lines_removed": total_removed,
            "change_types": change_types,
            "average_confidence": round(avg_confidence, 2),
            "confidence_breakdown": {
                "high": high_confidence,
                "medium": medium_confidence,
                "low": low_confidence,
            },
            "requires_manual_review": low_confidence > 0,
        }
