"""
Package registry client for fetching package metadata without downloading.
"""

from typing import Optional

import aiohttp


class PackageRegistryClient:
    """Client for interacting with package registries (PyPI, npm, Maven Central)."""

    PYPI_API = "https://pypi.org/pypi/{package}/json"
    NPM_API = "https://registry.npmjs.org/{package}"
    MAVEN_API = "https://search.maven.org/solrsearch/select?q=g:{group}+AND+a:{artifact}&rows=1&wt=json"

    def __init__(self):
        """Initialize the package registry client."""
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def get_latest_version(self, package_name: str, ecosystem: str) -> Optional[str]:
        """
        Get the latest version of a package without downloading it.

        Args:
            package_name: Name of the package
            ecosystem: Package ecosystem (python, javascript, java)

        Returns:
            Latest version string, or None if not found
        """
        if ecosystem == "python":
            return await self._get_pypi_latest(package_name)
        elif ecosystem == "javascript":
            return await self._get_npm_latest(package_name)
        elif ecosystem == "java":
            return await self._get_maven_latest(package_name)

        return None

    async def _get_pypi_latest(self, package_name: str) -> Optional[str]:
        """Get latest version from PyPI JSON API."""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            url = self.PYPI_API.format(package=package_name)
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("info", {}).get("version")
        except Exception as e:
            print(f"Error fetching PyPI data for {package_name}: {e}")

        return None

    async def _get_npm_latest(self, package_name: str) -> Optional[str]:
        """Get latest version from npm registry API."""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            url = self.NPM_API.format(package=package_name)
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("dist-tags", {}).get("latest")
        except Exception as e:
            print(f"Error fetching npm data for {package_name}: {e}")

        return None

    async def _get_maven_latest(self, package_name: str) -> Optional[str]:
        """Get latest version from Maven Central API."""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            # Parse groupId:artifactId format
            if ":" in package_name:
                group_id, artifact_id = package_name.split(":", 1)
            else:
                return None

            url = self.MAVEN_API.format(group=group_id, artifact=artifact_id)
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    docs = data.get("response", {}).get("docs", [])
                    if docs:
                        return docs[0].get("latestVersion")
        except Exception as e:
            print(f"Error fetching Maven data for {package_name}: {e}")

        return None

    async def get_package_metadata(
        self, package_name: str, version: str, ecosystem: str
    ) -> Optional[dict]:
        """
        Get detailed metadata for a specific package version.

        Args:
            package_name: Name of the package
            version: Specific version
            ecosystem: Package ecosystem

        Returns:
            Package metadata dict
        """
        if ecosystem == "python":
            return await self._get_pypi_metadata(package_name, version)
        elif ecosystem == "javascript":
            return await self._get_npm_metadata(package_name, version)

        return None

    async def _get_pypi_metadata(
        self, package_name: str, version: str
    ) -> Optional[dict]:
        """Get metadata for specific PyPI package version."""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            url = f"https://pypi.org/pypi/{package_name}/{version}/json"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    info = data.get("info", {})
                    return {
                        "name": info.get("name"),
                        "version": info.get("version"),
                        "release_date": data.get("urls", [{}])[0].get("upload_time", ""),
                        "homepage": info.get("home_page"),
                        "repository": info.get("project_urls", {}).get("Source"),
                        "description": info.get("summary"),
                    }
        except Exception as e:
            print(f"Error fetching PyPI metadata for {package_name}@{version}: {e}")

        return None

    async def _get_npm_metadata(
        self, package_name: str, version: str
    ) -> Optional[dict]:
        """Get metadata for specific npm package version."""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            url = self.NPM_API.format(package=package_name)
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    versions = data.get("versions", {})
                    if version in versions:
                        version_data = versions[version]
                        return {
                            "name": version_data.get("name"),
                            "version": version_data.get("version"),
                            "repository": version_data.get("repository", {}).get("url"),
                            "homepage": version_data.get("homepage"),
                            "description": version_data.get("description"),
                        }
        except Exception as e:
            print(f"Error fetching npm metadata for {package_name}@{version}: {e}")

        return None

