"""
LLM-based analyzer for extracting structured breaking changes from changelogs.

Uses Databricks Foundation Models or external LLM APIs to parse unstructured
changelog text and extract breaking changes in a structured format.
"""

import json
import logging
from typing import Optional
import aiohttp

from models.usage import APIChange


logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """Uses LLM to analyze changelogs and extract breaking changes."""

    def __init__(self):
        """Initialize the LLM analyzer."""
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def extract_breaking_changes(
        self,
        changelog_text: str,
        package_name: str,
        from_version: str,
        to_version: str,
    ) -> list[APIChange]:
        """
        Extract breaking changes from changelog text using LLM.

        Args:
            changelog_text: Raw changelog text
            package_name: Package name for context
            from_version: Starting version
            to_version: Target version

        Returns:
            List of structured APIChange objects
        """
        if not changelog_text or len(changelog_text) < 50:
            logger.warning("Changelog text too short for analysis")
            return []

        logger.info(
            f"🤖 Analyzing changelog with LLM for {package_name} ({len(changelog_text)} chars)"
        )

        # Create prompt for LLM
        prompt = self._create_analysis_prompt(
            changelog_text, package_name, from_version, to_version
        )

        # Call LLM (try Databricks FM first, fallback to simple parsing)
        try:
            api_changes = await self._call_llm_for_analysis(prompt)
            if api_changes:
                logger.info(f"✅ Extracted {len(api_changes)} changes from changelog")
                return api_changes
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}, falling back to heuristics")

        # Fallback: Use heuristic-based parsing
        return self._heuristic_breaking_change_extraction(
            changelog_text, package_name, from_version, to_version
        )

    def _create_analysis_prompt(
        self, changelog: str, package: str, from_ver: str, to_ver: str
    ) -> str:
        """Create a prompt for LLM to analyze changelog."""
        return f"""You are analyzing a software package changelog to identify breaking changes.

Package: {package}
Version range: {from_ver} → {to_ver}

Changelog text:
```
{changelog[:4000]}  # Limit to avoid token limits
```

Task: Extract ONLY breaking changes (changes that would break existing code).

A breaking change is:
- Removed function, class, or method
- Renamed function, class, or method
- Changed function signature (parameters added/removed/reordered)
- Changed required parameters
- Removed or changed default parameter values
- Deprecated APIs (if removal is imminent)

NOT breaking changes:
- New features added
- Bug fixes
- Performance improvements
- Internal implementation changes
- Optional parameters added

For each breaking change you find, provide:
1. change_type: one of ["removed", "renamed", "signature_changed", "deprecated"]
2. affected_item: the exact function/class/method name (e.g., "DataFrame.append", "ray.init")
3. old_signature: the old function signature (if applicable)
4. new_signature: the new function signature (if applicable)
5. migration_hint: specific advice on how to fix code (be concise)
6. severity: one of ["critical", "high", "medium", "low"]

Return ONLY a valid JSON array of breaking changes. Example format:
[
  {{
    "change_type": "removed",
    "affected_item": "DataFrame.append",
    "old_signature": "df.append(other, ignore_index=False, verify_integrity=False, sort=False)",
    "new_signature": null,
    "migration_hint": "Use pd.concat([df, other], ignore_index=True) instead",
    "severity": "high"
  }},
  {{
    "change_type": "signature_changed",
    "affected_item": "read_csv",
    "old_signature": "read_csv(filepath, sep=',', header='infer')",
    "new_signature": "read_csv(filepath, sep=',', header='infer', encoding=None)",
    "migration_hint": "Add encoding parameter if needed, None is now required to be explicit",
    "severity": "medium"
  }}
]

If no breaking changes are found, return an empty array: []

JSON output:"""

    async def _call_llm_for_analysis(self, prompt: str) -> list[APIChange]:
        """
        Call LLM API to analyze changelog.

        This is a placeholder - in production, this would call:
        - Databricks Foundation Model API
        - Claude API
        - OpenAI API
        - Or other LLM service
        """
        # TODO: Implement actual LLM API call
        # For now, return empty list to fall back to heuristics
        logger.info("ℹ️ LLM API integration not configured, using heuristics")
        return []

        # Example implementation (commented out):
        # try:
        #     # Call Databricks Foundation Model
        #     response = await self.session.post(
        #         "https://your-workspace.databricks.com/serving-endpoints/claude-3-sonnet/invocations",
        #         json={
        #             "messages": [{"role": "user", "content": prompt}],
        #             "max_tokens": 2000
        #         },
        #         headers={"Authorization": f"Bearer {your_token}"}
        #     )
        #     result = await response.json()
        #     # Parse LLM response and convert to APIChange objects
        #     return self._parse_llm_response(result)
        # except Exception as e:
        #     logger.error(f"LLM API call failed: {e}")
        #     return []

    def _parse_llm_response(self, response_text: str) -> list[APIChange]:
        """Parse LLM response into APIChange objects."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_text = response_text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0]

            changes_data = json.loads(json_text.strip())

            api_changes = []
            for change in changes_data:
                try:
                    api_change = APIChange(
                        package_name=change.get("package_name", ""),
                        from_version=change.get("from_version", ""),
                        to_version=change.get("to_version", ""),
                        change_type=change["change_type"],
                        affected_item=change["affected_item"],
                        old_signature=change.get("old_signature"),
                        new_signature=change.get("new_signature"),
                        migration_hint=change.get("migration_hint"),
                        is_breaking=True,
                        severity=change.get("severity", "medium"),
                    )
                    api_changes.append(api_change)
                except Exception as e:
                    logger.warning(f"Failed to parse change: {e}")
                    continue

            return api_changes

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return []

    def _heuristic_breaking_change_extraction(
        self, changelog: str, package: str, from_ver: str, to_ver: str
    ) -> list[APIChange]:
        """
        Fallback heuristic-based extraction of breaking changes.

        Looks for common patterns in changelogs:
        - "BREAKING CHANGE:", "Breaking:", "⚠️"
        - "Removed", "Deprecated", "Renamed"
        - "!:" prefix (conventional commits)
        """
        api_changes = []
        lines = changelog.split("\n")

        # Keywords that indicate breaking changes
        breaking_keywords = [
            "breaking change",
            "breaking:",
            "removed",
            "deprecated",
            "renamed",
            "⚠️",
            "!:",
            "incompatible",
            "backwards incompatible",
        ]

        in_breaking_section = False
        current_change = []

        for i, line in enumerate(lines):
            line_lower = line.lower()

            # Check if this line indicates a breaking change
            is_breaking_line = any(kw in line_lower for kw in breaking_keywords)

            if is_breaking_line:
                # Save previous change if any
                if current_change:
                    change = self._parse_breaking_change_lines(
                        current_change, package, from_ver, to_ver
                    )
                    if change:
                        api_changes.append(change)

                # Start new change
                current_change = [line]
                in_breaking_section = True
            elif in_breaking_section:
                # Continue collecting lines for current change
                if line.strip() and not line.startswith("#"):
                    current_change.append(line)
                elif line.startswith("#") or (i > 0 and lines[i - 1].strip() == ""):
                    # End of this breaking change section
                    if current_change:
                        change = self._parse_breaking_change_lines(
                            current_change, package, from_ver, to_ver
                        )
                        if change:
                            api_changes.append(change)
                    current_change = []
                    in_breaking_section = False

        # Don't forget the last one
        if current_change:
            change = self._parse_breaking_change_lines(
                current_change, package, from_ver, to_ver
            )
            if change:
                api_changes.append(change)

        if api_changes:
            logger.info(
                f"✅ Extracted {len(api_changes)} changes using heuristics"
            )
        else:
            logger.warning(
                f"⚠️ No breaking changes detected in changelog (may need manual review)"
            )

        return api_changes

    def _parse_breaking_change_lines(
        self, lines: list[str], package: str, from_ver: str, to_ver: str
    ) -> Optional[APIChange]:
        """Parse a group of lines describing a breaking change."""
        text = " ".join(lines).strip()

        # Determine change type
        change_type = "removed"
        if "deprecat" in text.lower():
            change_type = "deprecated"
        elif "renam" in text.lower():
            change_type = "renamed"
        elif "signature" in text.lower() or "parameter" in text.lower():
            change_type = "signature_changed"

        # Try to extract affected item (function/class name)
        # Look for patterns like `function_name`, ClassName, module.function
        import re

        affected_item = "unknown"
        # Pattern: `code`, code(), Class.method
        code_pattern = r"`([a-zA-Z_][a-zA-Z0-9_.]*)`|([a-zA-Z_][a-zA-Z0-9_.]*)\(\)"
        matches = re.findall(code_pattern, text)
        if matches:
            affected_item = matches[0][0] or matches[0][1]

        # Determine severity
        severity = "medium"
        if "critical" in text.lower() or "removed" in text.lower():
            severity = "high"
        if "deprecat" in text.lower():
            severity = "medium"

        return APIChange(
            package_name=package,
            from_version=from_ver,
            to_version=to_ver,
            change_type=change_type,
            affected_item=affected_item,
            migration_hint=text[:200],  # First 200 chars as hint
            is_breaking=True,
            severity=severity,
        )

