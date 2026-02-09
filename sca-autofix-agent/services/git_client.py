"""
Databricks Git/Repos client for repository operations.
"""

import logging
from typing import Optional

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import DatabricksError
from databricks.sdk.service.workspace import RepoInfo

logger = logging.getLogger(__name__)


class DatabricksGitClient:
    """Client for interacting with Databricks Repos (Git integration)."""

    def __init__(self, workspace_client: WorkspaceClient):
        """
        Initialize the Git client.

        Args:
            workspace_client: Authenticated Databricks workspace client
        """
        self.workspace_client = workspace_client

    def clone_repo(
        self,
        git_url: str,
        workspace_path: str,
        provider: str = "github",
        branch: Optional[str] = None,
    ) -> Optional[RepoInfo]:
        """
        Clone a Git repository into Databricks workspace.

        Args:
            git_url: Git repository URL (e.g., "https://github.com/org/repo.git")
            workspace_path: Destination path (e.g., "/Repos/user@company.com/my-repo")
            provider: Git provider - "github", "gitLab", "bitbucketCloud", or "azureDevOpsServices"
            branch: Optional specific branch to checkout after cloning

        Returns:
            RepoInfo object if successful, None otherwise
        """
        try:
            logger.info(f"Cloning {git_url} to {workspace_path}")

            # Create the repo (clone)
            repo = self.workspace_client.repos.create(
                url=git_url, provider=provider, path=workspace_path
            )

            logger.info(
                f"Repo cloned successfully: {repo.path} (branch: {repo.branch})"
            )

            # Optionally checkout a specific branch
            if branch and branch != repo.branch:
                logger.info(f"Switching to branch: {branch}")
                repo = self.workspace_client.repos.update(repo_id=repo.id, branch=branch)

            return repo

        except DatabricksError as e:
            logger.error(f"Error cloning repo: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error cloning repo: {e}")
            return None

    def list_repos(self, path_prefix: Optional[str] = None) -> list[RepoInfo]:
        """
        List all repositories in the workspace.

        Args:
            path_prefix: Optional path prefix to filter repos (e.g., "/Repos/user@company.com/")

        Returns:
            List of RepoInfo objects
        """
        try:
            repos = list(self.workspace_client.repos.list())

            if path_prefix:
                repos = [r for r in repos if r.path and r.path.startswith(path_prefix)]

            return repos

        except Exception as e:
            logger.error(f"Error listing repos: {e}")
            return []

    def delete_repo(self, repo_path: str) -> bool:
        """
        Delete a repository from the workspace.

        Args:
            repo_path: Path to the repo to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            repo_info = self.get_repo_info(repo_path)
            if repo_info and repo_info.id:
                self.workspace_client.repos.delete(repo_id=repo_info.id)
                logger.info(f"Repo deleted: {repo_path}")
                return True
            else:
                logger.warning(f"Repo not found: {repo_path}")
                return False

        except Exception as e:
            logger.error(f"Error deleting repo: {e}")
            return False

    def pull_changes(self, repo_path: str) -> bool:
        """
        Pull latest changes from remote repository.

        Args:
            repo_path: Path to the repo

        Returns:
            True if successful, False otherwise
        """
        try:
            repo_info = self.get_repo_info(repo_path)
            if repo_info and repo_info.id:
                current_branch = repo_info.branch
                # Update to the same branch triggers a pull
                self.workspace_client.repos.update(
                    repo_id=repo_info.id, branch=current_branch
                )
                logger.info(f"Pulled latest changes for {repo_path}")
                return True
            else:
                logger.warning(f"Repo not found: {repo_path}")
                return False

        except Exception as e:
            logger.error(f"Error pulling changes: {e}")
            return False

    def get_repo_info(self, repo_path: str) -> Optional[RepoInfo]:
        """
        Get information about a Databricks Repo.

        Args:
            repo_path: Path to the repo (e.g., /Repos/user@company.com/my-repo)

        Returns:
            RepoInfo object or None if not found
        """
        try:
            # Get repo by path
            repos = list(self.workspace_client.repos.list())
            for repo in repos:
                if repo.path == repo_path:
                    return repo
        except Exception as e:
            logger.error(f"Error getting repo info: {e}")

        return None

    def update_branch(self, repo_path: str, branch: str) -> bool:
        """
        Update a repo to a specific branch.

        Args:
            repo_path: Path to the repo
            branch: Branch name to checkout

        Returns:
            True if successful, False otherwise
        """
        try:
            repo_info = self.get_repo_info(repo_path)
            if repo_info and repo_info.id:
                self.workspace_client.repos.update(repo_id=repo_info.id, branch=branch)
                logger.info(f"Switched to branch '{branch}' for {repo_path}")
                return True
            else:
                logger.warning(f"Repo not found: {repo_path}")
        except Exception as e:
            logger.error(f"Error updating branch: {e}")

        return False

    def create_branch(self, repo_path: str, branch_name: str) -> bool:
        """
        Create a new branch in the repository.

        Note: Databricks Repos API doesn't directly support branch creation.
        This would need to be done through Git commands or the Git provider's API.

        Args:
            repo_path: Path to the repo
            branch_name: Name of the new branch

        Returns:
            True if successful, False otherwise
        """
        # In a real implementation, you would:
        # 1. Get the repo's Git URL
        # 2. Use the Git provider's API (GitHub, GitLab, etc.) to create the branch
        # 3. Then update the Databricks Repo to that branch

        logger.warning(
            f"Branch creation for '{branch_name}' would need to be implemented via Git provider API"
        )
        return False

    def apply_changes(
        self, repo_path: str, file_changes: dict, commit_message: str
    ) -> bool:
        """
        Apply file changes to a repository.

        Args:
            repo_path: Path to the repo
            file_changes: Dict of {file_path: new_content}
            commit_message: Commit message

        Returns:
            True if successful, False otherwise
        """
        try:
            # Write each file using workspace API
            for file_path, content in file_changes.items():
                full_path = f"{repo_path}/{file_path}"
                self.workspace_client.workspace.upload(
                    path=full_path,
                    content=content.encode("utf-8"),
                    overwrite=True,
                )

            # Note: Databricks Repos automatically syncs with Git
            # The commit would need to be done through Git provider API
            logger.info(f"Files updated in {repo_path}. Commit message: {commit_message}")
            logger.warning(
                "Note: Actual commit requires Git provider API integration"
            )
            return True

        except Exception as e:
            logger.error(f"Error applying changes: {e}")
            return False

    def get_current_branch(self, repo_path: str) -> Optional[str]:
        """
        Get the current branch of a repository.

        Args:
            repo_path: Path to the repo

        Returns:
            Branch name or None
        """
        repo_info = self.get_repo_info(repo_path)
        if repo_info:
            return repo_info.branch

        return None

