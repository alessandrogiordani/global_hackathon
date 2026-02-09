# Sample Data for SCA AutoFix Testing

This folder contains sample CSV datasets that can be uploaded to Databricks Unity Catalog for testing the SCA AutoFix solution.

## ⚠️ Real Open Source Repositories

The `sca_findings.csv` file uses **real open-source repositories** that are designed for security testing and intentionally contain vulnerable dependencies:

| Repository | URL | Description |
|------------|-----|-------------|
| **Snyk Java Goof** | https://github.com/snyk-labs/java-goof | Snyk's demo app with intentionally vulnerable Java dependencies (Jackson, Log4j, Tomcat, etc.) |
| **OWASP WebGoat** | https://github.com/WebGoat/WebGoat | OWASP's deliberately insecure Java app for learning security |
| **PMD** | https://github.com/pmd/pmd | Real Java static analyzer project (may have older dependency versions) |
| **Kubernetes Goat** | https://github.com/madhuakula/kubernetes-goat | Intentionally vulnerable K8s training environment |

These repos can be cloned by the agent for real testing!

## Tables Overview

| File | Table Name | Who Creates It | Purpose |
|------|------------|----------------|---------|
| `sca_findings.csv` | `sca_findings` | **INPUT** - SCA tool (Checkmarx) | Starting point - repos with vulns |
| `agent_analysis_results.csv` | `agent_analysis_results` | **OUTPUT** - Agent | Analysis results (sample for testing) |
| `user_decisions.csv` | `user_decisions` | **OUTPUT** - UI | User decisions (sample for testing) |
| `migration_analysis_results.csv` | `migration_analysis_results` | **OUTPUT** - Agent | Migration details (sample for testing) |
| `generated_patches.csv` | `generated_patches` | **OUTPUT** - Agent | Code patches (sample for testing) |

> **Note:** Only `sca_findings.csv` is required as input. The other CSVs are example outputs for testing/demo purposes.

## Table Schemas

### sca_findings (INPUT - Required)
Main input table - populated by SCA scanning tools (e.g., Checkmarx). One row per **repo + library** combination.

| Column | Type | Description |
|--------|------|-------------|
| repo_id | STRING | Unique identifier for this repo+library |
| repo_path | STRING | Databricks repo path (e.g., /repos/my-app) |
| repo_name | STRING | Human-readable repo name |
| repo_url | STRING | Git URL for cloning |
| library | STRING | Vulnerable library name |
| current_version | STRING | Current installed version |
| priority | STRING | Critical, High, Medium, Low |
| cve_ids | STRING (JSON) | Array of CVE identifiers |
| cvss_score | DOUBLE | CVSS severity score |
| candidate_versions | STRING (JSON) | Suggested safe versions |
| last_detected_ts | TIMESTAMP | When vulnerability was detected |
| status | STRING | ready, analyzing, approved, rejected |
| checkmarx_finding_id | STRING | Link to Checkmarx finding |
| owner_team | STRING | Team responsible for this repo |

### agent_analysis_results  
Output from agent analysis for each repo/version combination

| Column | Type | Description |
|--------|------|-------------|
| analysis_id | STRING | Unique analysis run ID |
| repo_id | STRING | Foreign key to sca_findings |
| target_version | STRING | Version being analyzed |
| code_changes_files | INT | Number of files to modify |
| code_changes_callsites | INT | Number of call sites affected |
| confidence | DOUBLE | Agent confidence score (0-1) |
| breaking_changes | STRING (JSON) | List of breaking changes detected |
| analysis_ts | TIMESTAMP | When analysis was performed |
| notes | STRING | Human-readable summary |

### user_decisions
Audit trail of human decisions

| Column | Type | Description |
|--------|------|-------------|
| decision_id | STRING | Unique decision ID |
| repo_id | STRING | Foreign key to sca_findings |
| target_version | STRING | Version decision applies to |
| decision | STRING | approved or rejected |
| user_email | STRING | User who made decision |
| decision_reason | STRING | Reason for decision |
| decision_ts | TIMESTAMP | When decision was made |

### migration_analysis_results
Detailed migration metrics

| Column | Type | Description |
|--------|------|-------------|
| migration_id | STRING | Unique migration analysis ID |
| repo_id | STRING | Foreign key to sca_findings |
| library | STRING | Library being upgraded |
| from_version | STRING | Current vulnerable version |
| to_version | STRING | Target safe version |
| breaking_changes_count | INT | Number of breaking changes |
| affected_files | INT | Files requiring modification |
| affected_invocations | INT | Method calls to update |
| patches_generated | INT | Total patches created |
| patches_high_confidence | INT | High confidence patches |
| patches_medium_confidence | INT | Medium confidence patches |
| patches_low_confidence | INT | Low confidence patches |
| migration_complexity | STRING | low, medium, high |
| estimated_effort_hours | DOUBLE | Estimated manual effort |
| auto_fixable_percent | DOUBLE | % that can be auto-fixed |
| analysis_ts | TIMESTAMP | Analysis timestamp |
| status | STRING | completed, pending_review, approved |

### generated_patches
Individual code changes

| Column | Type | Description |
|--------|------|-------------|
| patch_id | STRING | Unique patch ID |
| migration_id | STRING | Foreign key to migration_analysis_results |
| repo_id | STRING | Foreign key to sca_findings |
| file_path | STRING | File to modify |
| line_number | INT | Line number in file |
| change_type | STRING | method_removed, signature_changed, etc. |
| old_code | STRING | Original code snippet |
| new_code | STRING | Replacement code |
| confidence | STRING | high, medium, low |
| explanation | STRING | Why this change is needed |
| generated_by | STRING | Model that generated patch |
| generation_ts | TIMESTAMP | When patch was generated |

## Loading into Databricks

### Option 1: Upload via UI
1. Go to Databricks Workspace → Data
2. Select your catalog and schema (e.g., `ing_hackathon.sca_advisor`)
3. Click "Create Table" → "Upload File"
4. Upload each CSV and verify schema

### Option 2: Use the provided notebook
Run `load_sample_data.py` notebook in Databricks:

```python
# See load_sample_data.py in this folder
```

### Option 3: Databricks CLI
```bash
# Upload CSVs to DBFS
databricks fs cp sample_data/ dbfs:/FileStore/sca_sample_data/ --recursive

# Then run SQL to create tables (see load_sample_data.sql)
```

## Sample Scenarios

The sample data includes realistic test scenarios:

1. **Critical Jackson vulnerability** (repo_001, repo_005)
   - CVE-2020-36518: Denial of Service
   - Migration from 2.9.x to 2.15.x
   - Includes ObjectMapper breaking changes

2. **Log4Shell** (repo_002)
   - CVE-2021-44228: Remote Code Execution
   - Critical priority
   - High-confidence migration

3. **Spring Boot major upgrade** (repo_003)
   - Migration from 2.7 to 3.2
   - Many breaking changes
   - Shows rejection flow (user chose patch version instead)

4. **Multi-library vulnerabilities** (repo_005)
   - Both Jackson and SnakeYaml vulnerabilities
   - Shows handling of multiple CVEs in same repo

5. **Spring Security upgrade paths** (repo_006)
   - Two options: major (6.2) vs patch (5.8.9)
   - Shows decision-making between upgrade paths
