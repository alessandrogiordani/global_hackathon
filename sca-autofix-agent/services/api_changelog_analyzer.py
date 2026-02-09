"""
API Changelog Analyzer for detecting breaking changes between package versions.

For MVP, this uses a combination of:
1. Known breaking changes database (hardcoded for common packages)
2. PyPI release notes parsing (basic implementation)
3. Package version comparison heuristics

Future enhancements could include:
- Integration with API diff tools
- Machine learning-based breaking change detection
- Community-maintained breaking change databases
"""

import logging
import re
from typing import Optional
from packaging import version

from models.usage import APIChange, BreakingChangeReport, PackageUsageAnalysis
from services.changelog_fetcher import ChangelogFetcher
from services.llm_analyzer import LLMAnalyzer


logger = logging.getLogger(__name__)


# Known breaking changes for common packages (MVP dataset)
# Format: package_name -> {(from_version, to_version): [APIChange, ...]}
KNOWN_BREAKING_CHANGES = {
    "pandas": {
        ("1.x", "2.0"): [
            {
                "change_type": "removed",
                "affected_item": "DataFrame.append",
                "migration_hint": "Use pandas.concat() instead",
                "is_breaking": True,
                "severity": "high",
            },
            {
                "change_type": "signature_changed",
                "affected_item": "DataFrame.fillna",
                "old_signature": "fillna(value, method, axis, inplace, limit, downcast)",
                "new_signature": "fillna(value, method, axis, limit, downcast) - removed inplace parameter default",
                "migration_hint": "Explicitly set inplace=False or use df = df.fillna(...)",
                "is_breaking": True,
                "severity": "medium",
            },
        ],
    },
    "numpy": {
        ("1.19.x", "1.20"): [
            {
                "change_type": "deprecated",
                "affected_item": "np.int",
                "migration_hint": "Use built-in int or np.int_ instead",
                "is_breaking": True,
                "severity": "high",
            },
        ],
    },
    "requests": {
        ("2.x", "3.0"): [
            {
                "change_type": "removed",
                "affected_item": "requests.packages",
                "migration_hint": "Import urllib3 directly instead",
                "is_breaking": True,
                "severity": "medium",
            },
        ],
    },
    "tensorflow": {
        ("1.x", "2.0"): [
            {
                "change_type": "removed",
                "affected_item": "tf.Session",
                "migration_hint": "Use eager execution instead (default in TF 2.0)",
                "is_breaking": True,
                "severity": "critical",
            },
            {
                "change_type": "renamed",
                "affected_item": "tf.contrib",
                "migration_hint": "Most modules moved to separate packages or removed",
                "is_breaking": True,
                "severity": "critical",
            },
        ],
    },
}


class APIChangelogAnalyzer:
    """Analyzes API changes between package versions."""

    def __init__(self):
        """Initialize the API changelog analyzer."""
        self.known_changes = KNOWN_BREAKING_CHANGES

    async def check_breaking_changes(
        self,
        package_name: str,
        from_version: str,
        to_version: str,
        usage_analysis: Optional[PackageUsageAnalysis] = None,
        ecosystem: str = "python",
        use_changelog_analysis: bool = True,
    ) -> BreakingChangeReport:
        """
        Check for breaking changes between two versions of a package.

        Uses tiered approach:
        1. Check curated database (fast)
        2. Fetch and analyze changelog (accurate)
        3. Give up gracefully

        Args:
            package_name: Name of the package
            from_version: Current version
            to_version: Target upgrade version
            usage_analysis: Optional usage analysis to detect affected files
            ecosystem: Package ecosystem (python, javascript, etc.)
            use_changelog_analysis: Whether to fetch and analyze changelogs (default: True)

        Returns:
            BreakingChangeReport with detected breaking changes
        """
        logger.info(
            f"🔍 Checking breaking changes for {package_name}: {from_version} → {to_version}"
        )

        breaking_changes = []
        affected_files = set()
        analysis_method = "none"

        # Tier 1: Check known breaking changes database (instant)
        known_changes = self._get_known_changes(package_name, from_version, to_version)

        if known_changes:
            analysis_method = "curated_database"
            logger.info(f"✅ Found {len(known_changes)} known changes in database")

            for change_dict in known_changes:
                api_change = APIChange(
                    package_name=package_name,
                    from_version=from_version,
                    to_version=to_version,
                    change_type=change_dict["change_type"],
                    affected_item=change_dict["affected_item"],
                    old_signature=change_dict.get("old_signature"),
                    new_signature=change_dict.get("new_signature"),
                    migration_hint=change_dict.get("migration_hint"),
                    is_breaking=change_dict["is_breaking"],
                    severity=change_dict["severity"],
                )
                breaking_changes.append(api_change)

                # If we have usage analysis, check which files are affected
                if usage_analysis:
                    affected = self._find_affected_files(api_change, usage_analysis)
                    affected_files.update(affected)

        # Tier 2: Fetch and analyze changelog (if database had no results)
        elif use_changelog_analysis:
            logger.info(f"ℹ️ No known changes in database, fetching changelog...")
            try:
                async with ChangelogFetcher() as fetcher:
                    changelog_text = await fetcher.fetch_changelog(
                        package_name, from_version, to_version, ecosystem
                    )

                if changelog_text:
                    logger.info(f"📝 Changelog fetched, analyzing with LLM...")
                    async with LLMAnalyzer() as analyzer:
                        changelog_changes = await analyzer.extract_breaking_changes(
                            changelog_text, package_name, from_version, to_version
                        )

                    if changelog_changes:
                        analysis_method = "changelog_analysis"
                        breaking_changes.extend(changelog_changes)

                        # Check affected files
                        if usage_analysis:
                            for change in changelog_changes:
                                affected = self._find_affected_files(change, usage_analysis)
                                affected_files.update(affected)
                    else:
                        analysis_method = "changelog_found_no_breaking_changes"
                else:
                    analysis_method = "changelog_not_found"
                    logger.warning(f"⚠️ Could not fetch changelog for {package_name}")

            except Exception as e:
                logger.warning(f"⚠️ Changelog analysis failed: {e}")
                analysis_method = "changelog_analysis_failed"

        # Determine recommended action
        if not breaking_changes:
            if analysis_method in ["changelog_not_found", "changelog_analysis_failed", "none"]:
                recommended_action = "manual_review_required"
            else:
                recommended_action = "safe_to_upgrade"
        elif len(breaking_changes) <= 3 and not any(
            c.severity == "critical" for c in breaking_changes
        ):
            recommended_action = "manual_review_required"
        else:
            recommended_action = "do_not_upgrade"

        logger.info(
            f"✅ Analysis complete ({analysis_method}): {len(breaking_changes)} breaking changes affecting {len(affected_files)} files"
        )

        return BreakingChangeReport(
            package_name=package_name,
            from_version=from_version,
            to_version=to_version,
            breaking_changes=breaking_changes,
            affected_files=sorted(affected_files),
            total_breaking_changes=len(breaking_changes),
            migration_required=len(breaking_changes) > 0,
            recommended_action=recommended_action,
        )

    def _get_known_changes(
        self, package_name: str, from_version: str, to_version: str
    ) -> list[dict]:
        """Get known breaking changes for a package version range."""
        if package_name not in self.known_changes:
            logger.info(f"ℹ️ No known breaking changes data for {package_name} (using MVP dataset)")
            return []

        changes = []
        package_changes = self.known_changes[package_name]

        for (from_pattern, to_pattern), change_list in package_changes.items():
            if self._version_matches(from_version, from_pattern) and self._version_matches(
                to_version, to_pattern
            ):
                changes.extend(change_list)

        return changes

    def _version_matches(self, version_str: str, pattern: str) -> bool:
        """
        Check if a version matches a pattern.

        Patterns can be:
        - Exact version: "2.0.0"
        - Major version: "2.x"
        - Version range: ">=2.0"
        """
        try:
            if pattern.endswith(".x"):
                # Major version match
                major = pattern.split(".")[0]
                return version_str.startswith(major)
            elif pattern.startswith(">="):
                # Greater than or equal
                target = version.parse(pattern[2:])
                return version.parse(version_str) >= target
            elif pattern.startswith("<="):
                # Less than or equal
                target = version.parse(pattern[2:])
                return version.parse(version_str) <= target
            else:
                # Exact match
                return version.parse(version_str) == version.parse(pattern)
        except Exception as e:
            logger.warning(f"⚠️ Version comparison failed: {e}")
            return False

    def _find_affected_files(
        self, api_change: APIChange, usage_analysis: PackageUsageAnalysis
    ) -> list[str]:
        """Identify which files would be affected by an API change."""
        affected = []

        # Extract the method/class name from affected_item
        # e.g., "DataFrame.append" -> "append", "np.int" -> "int"
        if "." in api_change.affected_item:
            method_name = api_change.affected_item.split(".")[-1]
        else:
            method_name = api_change.affected_item

        # Check method usages
        for usage in usage_analysis.method_usages:
            if method_name in usage.method_name or method_name in usage.call_signature:
                affected.append(usage.file_path)

        # Check imports (for removed modules)
        for import_stmt in usage_analysis.imports:
            if method_name in import_stmt.package_name or any(
                method_name in item for item in import_stmt.imported_items
            ):
                affected.append(import_stmt.file_path)

        return list(set(affected))

    def add_known_change(
        self,
        package_name: str,
        from_version: str,
        to_version: str,
        change: dict,
    ) -> None:
        """
        Add a known breaking change to the database (for future enhancement).

        This allows the tool to learn from user feedback.
        """
        if package_name not in self.known_changes:
            self.known_changes[package_name] = {}

        key = (from_version, to_version)
        if key not in self.known_changes[package_name]:
            self.known_changes[package_name][key] = []

        self.known_changes[package_name][key].append(change)
        logger.info(f"✅ Added known change for {package_name} {from_version} → {to_version}")
