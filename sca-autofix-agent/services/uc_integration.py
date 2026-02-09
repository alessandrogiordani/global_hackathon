"""
Unity Catalog integration service for reading/writing vulnerability analysis data.

This service provides methods to:
- Read vulnerable repos from UC tables
- Write analysis results back to UC
- Record user decisions

Supports both:
- "mock" mode: Uses sample_data/sca_findings.csv for testing
- "production" mode: Uses Unity Catalog tables
"""

import logging
import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
import uuid

import pandas as pd


logger = logging.getLogger(__name__)


def _is_production_mode() -> bool:
    """Check if running in production mode."""
    return os.environ.get("DATA_MODE", "mock") == "production"


def _get_mock_data_path() -> Path:
    """Get path to mock data CSV file."""
    # Try multiple possible locations
    candidates = [
        Path(__file__).parent.parent.parent / "sample_data" / "sca_findings.csv",
        Path(__file__).parent.parent / "sample_data" / "sca_findings.csv",
        Path("sample_data/sca_findings.csv"),
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"Could not find sca_findings.csv in: {candidates}")


class UCIntegration:
    """Unity Catalog integration for vulnerability analysis workflow."""

    def __init__(self, catalog: str = "ing_hackathon", schema: str = "ing_hackathon"):
        """
        Initialize UC integration.

        Args:
            catalog: UC catalog name
            schema: UC schema name
        """
        self.catalog = catalog
        self.schema = schema
        self._connection = None
        self._mock_mode = not _is_production_mode()

        if self._mock_mode:
            logger.info("📋 UCIntegration running in MOCK mode (using CSV data)")
        else:
            logger.info(f"🔷 UCIntegration running in PRODUCTION mode (UC: {catalog}.{schema})")

    def _get_connection(self):
        """Get Databricks SQL connection using SDK authentication."""
        if self._mock_mode:
            return None

        if self._connection is None:
            try:
                from databricks import sql
                from databricks.sdk import WorkspaceClient
                
                # Use Databricks SDK for authentication (works in Databricks Apps)
                w = WorkspaceClient()
                
                # Get SQL warehouse HTTP path from environment or find one
                http_path = os.environ.get("SQL_WAREHOUSE_HTTP_PATH")
                
                if not http_path:
                    # Try to find an available SQL warehouse
                    warehouses = list(w.warehouses.list())
                    if warehouses:
                        # Prefer serverless, then running, then any
                        for wh in warehouses:
                            if wh.enable_serverless_compute:
                                http_path = f"/sql/1.0/warehouses/{wh.id}"
                                logger.info(f"🔷 Using serverless warehouse: {wh.name}")
                                break
                        if not http_path:
                            for wh in warehouses:
                                if str(wh.state) == "RUNNING":
                                    http_path = f"/sql/1.0/warehouses/{wh.id}"
                                    logger.info(f"🔷 Using running warehouse: {wh.name}")
                                    break
                        if not http_path:
                            wh = warehouses[0]
                            http_path = f"/sql/1.0/warehouses/{wh.id}"
                            logger.info(f"🔷 Using warehouse: {wh.name}")
                    else:
                        raise RuntimeError("No SQL warehouses available. Please configure SQL_WAREHOUSE_HTTP_PATH.")
                
                # Get hostname
                hostname = w.config.host.replace("https://", "").replace("http://", "")
                
                # Connect using SDK credentials
                self._connection = sql.connect(
                    server_hostname=hostname,
                    http_path=http_path,
                    credentials_provider=w.config.authenticate,
                )
                logger.info(f"✅ Connected to Databricks SQL at {hostname}")
            except ImportError as e:
                logger.error(f"❌ databricks-sql-connector not available: {e}")
                raise RuntimeError(
                    "databricks-sql-connector is required for UC integration. "
                    "Install with: pip install databricks-sql-connector"
                )
            except Exception as e:
                logger.error(f"❌ Failed to connect to Databricks SQL: {e}")
                raise
        return self._connection

    def _execute_query(self, query: str, fetch: bool = True) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame.
        
        Args:
            query: SQL query to execute
            fetch: Whether to fetch results (False for INSERT/UPDATE)
            
        Returns:
            DataFrame with results, or empty DataFrame for non-SELECT queries
        """
        connection = self._get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(query)
            if fetch and cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return pd.DataFrame(rows, columns=columns)
            return pd.DataFrame()
        finally:
            cursor.close()

    def _load_mock_data(self) -> pd.DataFrame:
        """Load mock data from CSV file."""
        csv_path = _get_mock_data_path()
        logger.info(f"📂 Loading mock data from: {csv_path}")

        df = pd.read_csv(csv_path)

        # Parse JSON columns
        if "cve_ids" in df.columns:
            df["cve_ids"] = df["cve_ids"].apply(
                lambda x: json.loads(x) if isinstance(x, str) else x
            )
        if "candidate_versions" in df.columns:
            df["candidate_versions"] = df["candidate_versions"].apply(
                lambda x: json.loads(x) if isinstance(x, str) else x
            )
        if "last_detected_ts" in df.columns:
            df["last_detected_ts"] = pd.to_datetime(df["last_detected_ts"])

        return df

    def get_sca_findings(
        self,
        status: Optional[str] = "ready",
        priority: Optional[int] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get vulnerable repositories from UC table or mock CSV.

        Args:
            status: Filter by status ('ready', 'analyzing', 'approved', 'rejected')
            priority: Filter by priority (1=Critical, 2=High, 3=Medium)
            limit: Maximum number of repos to return

        Returns:
            List of repo dictionaries matching the criteria
        """
        # =====================================================================
        # MOCK MODE: Load from CSV
        # =====================================================================
        if self._mock_mode:
            try:
                df = self._load_mock_data()

                # Apply filters
                if status:
                    df = df[df["status"] == status]

                if priority:
                    priority_map = {
                        1: "Critical",
                        2: "High",
                        3: "Medium",
                        4: "Low",
                        5: "Informational",
                    }
                    if isinstance(priority, int):
                        priority_str = priority_map.get(priority, "Medium")
                    else:
                        priority_str = priority
                    df = df[df["priority"] == priority_str]

                # Apply limit
                df = df.head(limit)

                repos = df.to_dict("records")
                logger.info(f"✅ Retrieved {len(repos)} repos from mock CSV")
                return repos

            except Exception as e:
                logger.error(f"❌ Failed to load mock data: {e}")
                raise

        # =====================================================================
        # PRODUCTION MODE: Query Unity Catalog via Databricks SQL
        # =====================================================================
        try:
            # Build query - flat schema (one row per repo+library)
            query = f"""
                SELECT 
                    repo_id,
                    repo_path,
                    repo_name,
                    repo_url,
                    library,
                    current_version,
                    priority,
                    cve_ids,
                    cvss_score,
                    candidate_versions,
                    last_detected_ts,
                    status,
                    checkmarx_finding_id,
                    owner_team
                FROM {self.catalog}.{self.schema}.sca_findings
                WHERE 1=1
            """

            if status:
                query += f" AND status = '{status}'"

            if priority:
                # Support both string and int priority
                if isinstance(priority, int):
                    priority_map = {
                        1: "Critical",
                        2: "High",
                        3: "Medium",
                        4: "Low",
                        5: "Informational",
                    }
                    priority_str = priority_map.get(priority, "Medium")
                    query += f" AND priority = '{priority_str}'"
                else:
                    query += f" AND priority = '{priority}'"

            query += f" LIMIT {limit}"

            logger.info(f"📊 Querying UC table: {query}")

            df = self._execute_query(query)
            
            # Parse JSON columns if they're strings
            if "cve_ids" in df.columns:
                df["cve_ids"] = df["cve_ids"].apply(
                    lambda x: json.loads(x) if isinstance(x, str) else x
                )
            if "candidate_versions" in df.columns:
                df["candidate_versions"] = df["candidate_versions"].apply(
                    lambda x: json.loads(x) if isinstance(x, str) else x
                )
            
            repos = df.to_dict("records")

            logger.info(f"✅ Retrieved {len(repos)} repos from UC")
            return repos

        except Exception as e:
            logger.error(f"❌ Failed to query UC table: {e}")
            raise

    def write_analysis_result(
        self,
        repo_id: str,
        target_version: str,
        code_changes_files: int,
        code_changes_callsites: int,
        confidence: float,
        breaking_changes: list[str],
        notes: str = "",
    ) -> str:
        """
        Write agent analysis results to UC table.

        Args:
            repo_id: Repository ID
            target_version: Version being analyzed
            code_changes_files: Number of files requiring changes
            code_changes_callsites: Number of call sites to modify
            confidence: Confidence score (0-1)
            breaking_changes: List of breaking changes detected
            notes: Additional notes

        Returns:
            analysis_id: Generated UUID for this analysis
        """
        analysis_id = str(uuid.uuid4())
        analysis_ts = datetime.now()

        # =====================================================================
        # MOCK MODE: Log and return (no persistence)
        # =====================================================================
        if self._mock_mode:
            logger.info(f"📋 [MOCK] Would write analysis result:")
            logger.info(f"   analysis_id: {analysis_id}")
            logger.info(f"   repo_id: {repo_id}")
            logger.info(f"   target_version: {target_version}")
            logger.info(f"   code_changes_files: {code_changes_files}")
            logger.info(f"   confidence: {confidence}")
            return analysis_id

        # =====================================================================
        # PRODUCTION MODE: Write to Unity Catalog via SQL
        # =====================================================================
        try:
            # Escape string values and format for SQL
            breaking_changes_json = json.dumps(breaking_changes).replace("'", "''")
            notes_escaped = notes.replace("'", "''")
            analysis_ts_str = analysis_ts.strftime("%Y-%m-%d %H:%M:%S")

            table_name = f"{self.catalog}.{self.schema}.agent_analysis_results"
            
            insert_sql = f"""
                INSERT INTO {table_name} 
                (analysis_id, repo_id, target_version, code_changes_files, 
                 code_changes_callsites, confidence, breaking_changes, analysis_ts, notes)
                VALUES (
                    '{analysis_id}',
                    '{repo_id}',
                    '{target_version}',
                    {code_changes_files},
                    {code_changes_callsites},
                    {float(confidence)},
                    '{breaking_changes_json}',
                    '{analysis_ts_str}',
                    '{notes_escaped}'
                )
            """
            
            self._execute_query(insert_sql, fetch=False)

            logger.info(f"✅ Wrote analysis result {analysis_id} to UC")
            return analysis_id

        except Exception as e:
            logger.error(f"❌ Failed to write analysis to UC: {e}")
            raise

    def record_user_decision(
        self,
        repo_id: str,
        target_version: str,
        decision: str,
        user_email: str,
        decision_reason: str = "",
    ) -> str:
        """
        Record user decision (approve/reject) to UC audit table.

        Args:
            repo_id: Repository ID
            target_version: Version decision applies to
            decision: 'approved' or 'rejected'
            user_email: User making the decision
            decision_reason: Reason for the decision

        Returns:
            decision_id: Generated UUID for this decision
        """
        decision_id = str(uuid.uuid4())
        decision_ts = datetime.now()

        # =====================================================================
        # MOCK MODE: Log and return (no persistence)
        # =====================================================================
        if self._mock_mode:
            logger.info(f"📋 [MOCK] Would record user decision:")
            logger.info(f"   decision_id: {decision_id}")
            logger.info(f"   repo_id: {repo_id}")
            logger.info(f"   decision: {decision}")
            logger.info(f"   user_email: {user_email}")
            return decision_id

        # =====================================================================
        # PRODUCTION MODE: Write to Unity Catalog via SQL
        # =====================================================================
        try:
            # Escape string values for SQL
            decision_reason_escaped = decision_reason.replace("'", "''")
            decision_ts_str = decision_ts.strftime("%Y-%m-%d %H:%M:%S")

            table_name = f"{self.catalog}.{self.schema}.user_decisions"
            
            insert_sql = f"""
                INSERT INTO {table_name} 
                (decision_id, repo_id, target_version, decision, user_email, 
                 decision_reason, decision_ts)
                VALUES (
                    '{decision_id}',
                    '{repo_id}',
                    '{target_version}',
                    '{decision}',
                    '{user_email}',
                    '{decision_reason_escaped}',
                    '{decision_ts_str}'
                )
            """
            
            self._execute_query(insert_sql, fetch=False)

            logger.info(f"✅ Recorded decision {decision_id} to UC")
            return decision_id

        except Exception as e:
            logger.error(f"❌ Failed to record decision to UC: {e}")
            raise

    def update_repo_status(self, repo_id: str, new_status: str) -> bool:
        """
        Update repository status in UC table.

        Args:
            repo_id: Repository ID
            new_status: New status ('ready', 'analyzing', 'approved', 'rejected')

        Returns:
            Success boolean
        """
        # =====================================================================
        # MOCK MODE: Log only
        # =====================================================================
        if self._mock_mode:
            logger.info(f"📋 [MOCK] Would update repo {repo_id} status to {new_status}")
            return True

        # =====================================================================
        # PRODUCTION MODE: Update in Unity Catalog via SQL
        # =====================================================================
        try:
            # Update using SQL
            query = f"""
                UPDATE {self.catalog}.{self.schema}.sca_findings
                SET status = '{new_status}'
                WHERE repo_id = '{repo_id}'
            """

            self._execute_query(query, fetch=False)
            logger.info(f"✅ Updated repo {repo_id} status to {new_status}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to update repo status: {e}")
            return False

    def get_analysis_history(self, repo_id: str, limit: int = 10) -> list[dict]:
        """
        Get analysis history for a repository.

        Args:
            repo_id: Repository ID
            limit: Maximum number of results

        Returns:
            List of analysis results
        """
        # =====================================================================
        # MOCK MODE: Return empty (no history in mock)
        # =====================================================================
        if self._mock_mode:
            logger.info(f"📋 [MOCK] No analysis history available in mock mode")
            return []

        # =====================================================================
        # PRODUCTION MODE: Query Unity Catalog via SQL
        # =====================================================================
        try:
            query = f"""
                SELECT *
                FROM {self.catalog}.{self.schema}.agent_analysis_results
                WHERE repo_id = '{repo_id}'
                ORDER BY analysis_ts DESC
                LIMIT {limit}
            """

            df = self._execute_query(query)
            results = df.to_dict("records")

            logger.info(f"✅ Retrieved {len(results)} analysis results for {repo_id}")
            return results

        except Exception as e:
            logger.error(f"❌ Failed to get analysis history: {e}")
            raise

    def get_java_repos_to_scan(
        self,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        table: str = "java_repos_to_scan",
        limit: int = 100,
    ) -> list[dict]:
        """
        Get list of Java repositories to scan from UC table.

        Expected table schema:
        - repo_url (STRING): Git repository URL
        - ref (STRING): Branch/tag/commit to scan
        - repo_name (STRING): Human-readable name
        - priority (INT, optional): Scan priority

        Args:
            catalog: UC catalog (defaults to self.catalog)
            schema: UC schema (defaults to self.schema)
            table: UC table name
            limit: Maximum number of repos to return

        Returns:
            List of repo dictionaries with keys: repo_url, ref, repo_name
        """
        cat = catalog or self.catalog
        sch = schema or self.schema

        try:
            query = f"""
                SELECT 
                    repo_url,
                    COALESCE(ref, 'main') as ref,
                    repo_name
                FROM {cat}.{sch}.{table}
                LIMIT {limit}
            """

            logger.info(f"📊 Querying Java repos from: {cat}.{sch}.{table}")

            df = self._execute_query(query)
            repos = df.to_dict("records")

            logger.info(f"✅ Retrieved {len(repos)} Java repos to scan")
            return repos

        except Exception as e:
            logger.error(f"❌ Failed to query Java repos table: {e}")
            raise

    def write_java_analysis_results(
        self,
        results: list[dict],
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        table: str = "java_analysis_results",
    ) -> int:
        """
        Write Java analysis results to UC table.

        Args:
            results: List of JavaAnalysisResult dictionaries
            catalog: UC catalog (defaults to self.catalog)
            schema: UC schema (defaults to self.schema)
            table: UC table name

        Returns:
            Number of rows written
        """
        cat = catalog or self.catalog
        sch = schema or self.schema

        try:
            analysis_ts = datetime.now()
            analysis_ts_str = analysis_ts.strftime("%Y-%m-%d %H:%M:%S")
            table_name = f"{cat}.{sch}.{table}"

            # Insert each result as a separate row
            for result in results:
                analysis_id = str(uuid.uuid4())
                summary_json = json.dumps(result.get("summary", {})).replace("'", "''")
                error_val = result.get("error")
                error_escaped = f"'{error_val.replace(chr(39), chr(39)+chr(39))}'" if error_val else "NULL"
                
                insert_sql = f"""
                    INSERT INTO {table_name} 
                    (analysis_id, repo_url, repo_name, ref, total_files, total_calls,
                     parse_success_count, parse_error_count, summary, analysis_ts, status, error)
                    VALUES (
                        '{analysis_id}',
                        '{result.get("repo_url", "")}',
                        '{result.get("repo_name", "")}',
                        '{result.get("ref", "")}',
                        {result.get("total_files", 0)},
                        {result.get("total_calls", 0)},
                        {result.get("parse_success_count", 0)},
                        {result.get("parse_error_count", 0)},
                        '{summary_json}',
                        '{analysis_ts_str}',
                        '{result.get("status", "success")}',
                        {error_escaped}
                    )
                """
                self._execute_query(insert_sql, fetch=False)

            logger.info(f"✅ Wrote {len(results)} Java analysis results to {table_name}")
            return len(results)

        except Exception as e:
            logger.error(f"❌ Failed to write Java analysis results: {e}")
            raise

    def write_migration_analysis(
        self,
        repo_id: str,
        library: str,
        from_version: str,
        to_version: str,
        breaking_changes: list,
        patches: list,
        summary: dict,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        table: str = "migration_analysis_results",
    ) -> str:
        """
        Write library migration analysis results to UC table.

        Args:
            repo_id: Repository ID
            library: Library name
            from_version: Current version
            to_version: Target version
            breaking_changes: List of breaking changes
            patches: List of generated patches
            summary: Summary statistics
            catalog: UC catalog (defaults to self.catalog)
            schema: UC schema (defaults to self.schema)
            table: UC table name

        Returns:
            analysis_id: Generated UUID
        """
        cat = catalog or self.catalog
        sch = schema or self.schema

        try:
            analysis_id = str(uuid.uuid4())
            analysis_ts = datetime.now()
            analysis_ts_str = analysis_ts.strftime("%Y-%m-%d %H:%M:%S")
            table_name = f"{cat}.{sch}.{table}"

            # Escape JSON data for SQL
            breaking_changes_json = json.dumps(breaking_changes).replace("'", "''")
            patches_json = json.dumps(patches).replace("'", "''")

            insert_sql = f"""
                INSERT INTO {table_name} 
                (analysis_id, repo_id, library, from_version, to_version,
                 breaking_changes_count, affected_files, affected_invocations,
                 breaking_changes, patches, migration_complexity, 
                 estimated_effort_hours, auto_fixable_percent,
                 patches_generated, patches_high_confidence, 
                 patches_medium_confidence, patches_low_confidence,
                 analysis_ts, status)
                VALUES (
                    '{analysis_id}',
                    '{repo_id}',
                    '{library}',
                    '{from_version}',
                    '{to_version}',
                    {summary.get("breaking_changes_count", 0)},
                    {summary.get("affected_files", 0)},
                    {summary.get("affected_invocations", 0)},
                    '{breaking_changes_json}',
                    '{patches_json}',
                    '{summary.get("migration_complexity", "medium")}',
                    {summary.get("estimated_effort_hours", 0.0)},
                    {summary.get("auto_fixable_percent", 0.0)},
                    {summary.get("patches_generated", 0)},
                    {summary.get("patches_high_confidence", 0)},
                    {summary.get("patches_medium_confidence", 0)},
                    {summary.get("patches_low_confidence", 0)},
                    '{analysis_ts_str}',
                    'completed'
                )
            """
            
            self._execute_query(insert_sql, fetch=False)

            logger.info(f"✅ Wrote migration analysis {analysis_id} to {table_name}")
            return analysis_id

        except Exception as e:
            logger.error(f"❌ Failed to write migration analysis: {e}")
            raise
