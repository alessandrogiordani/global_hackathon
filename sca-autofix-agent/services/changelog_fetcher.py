"""
Changelog fetcher for extracting release notes and changelogs from various sources.

This service fetches changelogs from:
1. GitHub releases
2. PyPI project metadata
3. Common changelog files (CHANGELOG.md, HISTORY.md, etc.)
4. npm registry
"""

import logging
import re
from typing import Optional
import aiohttp
from packaging import version


logger = logging.getLogger(__name__)


class ChangelogFetcher:
    """Fetches changelogs from various package registries and repositories."""

    def __init__(self):
        """Initialize the changelog fetcher."""
        self.session: Optional[aiohttp.ClientSession] = None
        self._github_token = None  # Optional: for rate limits

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def fetch_changelog(
        self,
        package_name: str,
        from_version: str,
        to_version: str,
        ecosystem: str = "python",
    ) -> Optional[str]:
        """
        Fetch changelog text between two versions.

        Args:
            package_name: Name of the package
            from_version: Starting version
            to_version: Target version
            ecosystem: Package ecosystem (python, javascript, java)

        Returns:
            Changelog text or None if not found
        """
        logger.info(
            f"📰 Fetching changelog for {package_name}: {from_version} → {to_version}"
        )

        if ecosystem == "python":
            return await self._fetch_python_changelog(
                package_name, from_version, to_version
            )
        elif ecosystem == "javascript":
            return await self._fetch_javascript_changelog(
                package_name, from_version, to_version
            )
        else:
            logger.warning(f"Unsupported ecosystem: {ecosystem}")
            return None

    async def _fetch_python_changelog(
        self, package_name: str, from_version: str, to_version: str
    ) -> Optional[str]:
        """Fetch changelog for a Python package."""

        # Step 1: Get GitHub repository URL from PyPI
        github_repo = await self._get_github_repo_from_pypi(package_name)

        if github_repo:
            # Try GitHub releases first (most structured)
            changelog = await self._fetch_github_releases(
                github_repo, from_version, to_version
            )
            if changelog:
                logger.info(f"✅ Found changelog from GitHub releases")
                return changelog

            # Try common changelog files
            for filename in ["CHANGELOG.md", "HISTORY.md", "RELEASES.md", "NEWS.md"]:
                changelog = await self._fetch_github_file(github_repo, filename)
                if changelog:
                    # Extract relevant version range
                    extracted = self._extract_version_range(
                        changelog, from_version, to_version
                    )
                    if extracted:
                        logger.info(f"✅ Found changelog from {filename}")
                        return extracted

        # Try PyPI project description as last resort
        pypi_description = await self._fetch_pypi_description(package_name)
        if pypi_description and len(pypi_description) > 100:
            logger.info(f"⚠️ Using PyPI description (may not be accurate)")
            return pypi_description

        logger.warning(f"❌ No changelog found for {package_name}")
        return None

    async def _get_github_repo_from_pypi(self, package_name: str) -> Optional[str]:
        """Get GitHub repository URL from PyPI metadata."""
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    info = data.get("info", {})

                    # Check project_urls first
                    project_urls = info.get("project_urls", {})
                    for key in [
                        "Source",
                        "Repository",
                        "Source Code",
                        "Homepage",
                        "Code",
                    ]:
                        url = project_urls.get(key, "")
                        if "github.com" in url:
                            return self._normalize_github_url(url)

                    # Check homepage
                    homepage = info.get("home_page", "")
                    if "github.com" in homepage:
                        return self._normalize_github_url(homepage)

        except Exception as e:
            logger.warning(f"Failed to fetch PyPI metadata: {e}")

        return None

    def _normalize_github_url(self, url: str) -> Optional[str]:
        """Normalize GitHub URL to owner/repo format."""
        # Extract owner/repo from various GitHub URL formats
        match = re.search(r"github\.com[:/]([^/]+)/([^/\s.]+)", url)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
        return None

    async def _fetch_github_releases(
        self, repo: str, from_version: str, to_version: str
    ) -> Optional[str]:
        """Fetch release notes from GitHub releases API."""
        try:
            # GitHub API endpoint
            url = f"https://api.github.com/repos/{repo}/releases"
            headers = {}
            if self._github_token:
                headers["Authorization"] = f"token {self._github_token}"

            async with self.session.get(
                url, headers=headers, timeout=10
            ) as response:
                if response.status == 200:
                    releases = await response.json()

                    # Filter releases in version range
                    relevant_releases = []
                    try:
                        from_ver = version.parse(from_version)
                        to_ver = version.parse(to_version)

                        for release in releases:
                            tag = release.get("tag_name", "").lstrip("v")
                            try:
                                release_ver = version.parse(tag)
                                if from_ver < release_ver <= to_ver:
                                    relevant_releases.append(release)
                            except Exception:
                                continue

                    except Exception:
                        # If version parsing fails, just get recent releases
                        relevant_releases = releases[:10]

                    if relevant_releases:
                        # Combine release notes
                        changelog_parts = []
                        for release in relevant_releases:
                            tag = release.get("tag_name", "unknown")
                            body = release.get("body", "")
                            if body:
                                changelog_parts.append(f"## {tag}\n\n{body}\n")

                        return "\n".join(changelog_parts)

        except Exception as e:
            logger.warning(f"Failed to fetch GitHub releases: {e}")

        return None

    async def _fetch_github_file(self, repo: str, filename: str) -> Optional[str]:
        """Fetch a specific file from GitHub repo."""
        try:
            # Try main branch first, then master
            for branch in ["main", "master"]:
                url = f"https://raw.githubusercontent.com/{repo}/{branch}/{filename}"
                async with self.session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.text()
        except Exception as e:
            logger.debug(f"Failed to fetch {filename} from GitHub: {e}")

        return None

    def _extract_version_range(
        self, changelog: str, from_version: str, to_version: str
    ) -> Optional[str]:
        """Extract relevant portion of changelog between versions."""
        try:
            # Find version headers in changelog
            # Common patterns: ## 2.0.0, # Version 2.0.0, ## [2.0.0], etc.
            version_pattern = r"##?\s*(?:\[)?v?(\d+\.\d+(?:\.\d+)?)"

            lines = changelog.split("\n")
            relevant_lines = []
            in_range = False
            from_ver = version.parse(from_version)
            to_ver = version.parse(to_version)

            for line in lines:
                match = re.match(version_pattern, line)
                if match:
                    try:
                        ver = version.parse(match.group(1))
                        if ver <= to_ver and ver > from_ver:
                            in_range = True
                            relevant_lines.append(line)
                        elif ver <= from_ver:
                            in_range = False
                            break
                    except Exception:
                        continue
                elif in_range:
                    relevant_lines.append(line)

            if relevant_lines:
                return "\n".join(relevant_lines)

        except Exception as e:
            logger.debug(f"Failed to extract version range: {e}")

        # If extraction fails, return first ~5000 chars (recent changes)
        return changelog[:5000] if changelog else None

    async def _fetch_pypi_description(self, package_name: str) -> Optional[str]:
        """Fetch package description from PyPI."""
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("info", {}).get("description", "")
        except Exception as e:
            logger.warning(f"Failed to fetch PyPI description: {e}")

        return None

    async def _fetch_javascript_changelog(
        self, package_name: str, from_version: str, to_version: str
    ) -> Optional[str]:
        """Fetch changelog for a JavaScript/npm package."""
        try:
            # Get package metadata from npm registry
            url = f"https://registry.npmjs.org/{package_name}"
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()

                    # Check for repository URL
                    repo = data.get("repository", {})
                    if isinstance(repo, dict):
                        repo_url = repo.get("url", "")
                    else:
                        repo_url = str(repo)

                    if "github.com" in repo_url:
                        github_repo = self._normalize_github_url(repo_url)
                        if github_repo:
                            return await self._fetch_github_releases(
                                github_repo, from_version, to_version
                            )

        except Exception as e:
            logger.warning(f"Failed to fetch npm changelog: {e}")

        return None

