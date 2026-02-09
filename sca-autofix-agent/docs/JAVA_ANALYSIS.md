# Java Code Analysis with Temporary Cloning

## 🎯 Overview

The vulnerability scanner now supports **Java code analysis** using `javalang` AST parsing with **temporary cloning** for automatic cleanup.

### What It Does

- 📥 Clones Java repositories from Git (temporary, auto-cleanup)
- 🔍 Finds all `.java` files
- 🧠 Parses Java code with `javalang` (no JVM required!)
- 📊 Extracts:
  - Class/interface/enum structures
  - Method invocations (API calls)
  - Package organization
- 💾 Writes results to Unity Catalog

---

## 🚀 Quick Start

### 1. Create UC Table with Repos to Scan

```sql
CREATE TABLE main.security.java_repos_to_scan (
  repo_url STRING COMMENT 'Git repository URL',
  ref STRING COMMENT 'Branch/tag/commit (default: main)',
  repo_name STRING COMMENT 'Human-readable name'
);

-- Add some repos
INSERT INTO main.security.java_repos_to_scan VALUES
  ('https://github.com/spring-projects/spring-boot.git', 'main', 'Spring Boot'),
  ('https://github.com/apache/kafka.git', 'trunk', 'Apache Kafka'),
  ('https://github.com/mybatis/mybatis-3.git', 'master', 'MyBatis');
```

### 2. Create UC Results Table

```sql
CREATE TABLE main.security.java_analysis_results (
  analysis_id STRING COMMENT 'Unique analysis ID',
  repo_url STRING COMMENT 'Repository URL',
  repo_name STRING COMMENT 'Repository name',
  ref STRING COMMENT 'Branch/tag analyzed',
  total_files INT COMMENT 'Total Java files found',
  total_calls INT COMMENT 'Total method invocations',
  parse_success_count INT COMMENT 'Successfully parsed files',
  parse_error_count INT COMMENT 'Files with parse errors',
  summary STRUCT<
    unique_packages: ARRAY<STRING>,
    unique_classes: ARRAY<STRING>,
    unique_method_calls: ARRAY<STRING>,
    package_count: INT,
    class_count: INT,
    unique_method_count: INT
  > COMMENT 'Summary statistics',
  analysis_ts TIMESTAMP COMMENT 'Analysis timestamp',
  status STRING COMMENT 'success or error',
  error STRING COMMENT 'Error message if failed'
);
```

### 3. Run Analysis

In AI Playground or via MCP client:

```
User: "Analyze all Java repos in the security table"

Agent calls:
→ analyze_java_repos_from_uc(
    catalog="main",
    schema="security", 
    table="java_repos_to_scan"
  )
```

---

## 📊 What You Get

### Analysis Results

For each repository:

```json
{
  "repo_url": "https://github.com/spring-projects/spring-boot.git",
  "repo_name": "Spring Boot",
  "ref": "main",
  "total_files": 2847,
  "total_calls": 45632,
  "parse_success_count": 2840,
  "parse_error_count": 7,
  "summary": {
    "unique_packages": ["org.springframework.boot", "org.springframework.boot.autoconfigure", ...],
    "unique_classes": ["SpringApplication", "ConfigurationProperties", ...],
    "unique_method_calls": ["info", "debug", "error", "save", "findById", ...],
    "package_count": 127,
    "class_count": 2840,
    "unique_method_count": 1523
  }
}
```

### Method Call Details (stored in Pydantic models)

Each method invocation includes:
- **File path**: `src/main/java/com/example/UserService.java`
- **Line number**: `42`
- **Caller context**: Class `UserService`, method `saveUser`
- **Callee info**: `logger.info()` with 1 argument

---

## 🔍 Use Cases

### 1. Security Audit

**Scenario**: Log4j vulnerability discovered

```sql
-- Query for log4j usage
SELECT 
  repo_name,
  total_calls,
  summary.unique_method_calls
FROM main.security.java_analysis_results
WHERE array_contains(summary.unique_packages, 'org.apache.logging.log4j');
```

**Result**: Know exactly which repos use Log4j and which methods are called

### 2. Migration Planning

**Scenario**: Upgrading Java version or library

```sql
-- Find repos using deprecated APIs
SELECT 
  repo_name,
  total_files,
  total_calls
FROM main.security.java_analysis_results
WHERE array_contains(summary.unique_method_calls, 'finalize')  -- deprecated in Java 9
   OR array_contains(summary.unique_method_calls, 'stop');     -- deprecated Thread.stop()
```

### 3. Dependency Analysis

**Scenario**: Understanding API usage patterns

```sql
-- Most commonly called methods
SELECT 
  explode(summary.unique_method_calls) as method_name,
  count(*) as repo_count
FROM main.security.java_analysis_results
GROUP BY method_name
ORDER BY repo_count DESC
LIMIT 20;
```

---

## ⚙️ How It Works

### Architecture

```
UC Table → MCP Tool → JavaAnalyzer → Temp Clone → javalang → Results → UC Table
   ↓                        ↓              ↓           ↓           ↓
 Repos      Read list    For each    git clone   Parse AST    Write back
```

### Step-by-Step

1. **Read UC Table**: Get list of repos to analyze
2. **Temporary Clone**: Each repo is cloned to `/tmp/{unique-id}/repo`
3. **Find Java Files**: Recursively search for `*.java` (excludes target/, build/, etc.)
4. **Parse with javalang**: Convert Java source → Python AST
5. **Extract Data**:
   - Structures: packages, classes, interfaces
   - Invocations: every `object.method()` call
6. **Auto-Cleanup**: Temp directory deleted automatically
7. **Write to UC**: Results stored in `java_analysis_results` table

### Why Temporary Clone?

✅ **Automatic cleanup** - No workspace pollution  
✅ **No persistent storage** - Repos deleted after analysis  
✅ **Stateless** - Each run is independent  
✅ **Scalable** - Can analyze hundreds of repos  

---

## 🛠️ Technical Details

### Excluded Directories

The analyzer automatically skips:
- `.git` - Git metadata
- `.idea`, `.vscode` - IDE files
- `target`, `build`, `out` - Build outputs
- `.gradle`, `.mvn` - Build tool files
- `node_modules` - JavaScript dependencies

### Parse Success vs. Errors

- **Success**: Valid Java syntax, AST created
- **Error**: Syntax errors, incomplete files, corrupted files

**Note**: Parse errors are tracked but don't stop analysis

### Performance

- **Shallow clone**: Uses `--depth 1` for speed
- **Parallel potential**: Could analyze repos in parallel (not implemented yet)
- **Memory**: Temp files cleaned immediately after each repo

---

## 🔧 Configuration

### Custom UC Locations

```python
# Different catalog/schema
analyze_java_repos_from_uc(
    catalog="production",
    schema="security_audit",
    table="vulnerable_java_apps"
)
```

### Environment Requirements

- ✅ `git` binary in PATH (for cloning)
- ✅ PySpark available (Databricks runtime)
- ✅ `javalang==0.13.0` installed
- ✅ Network access (for cloning)

---

## 📝 Example Agent Workflow

**User**: "We found a critical vulnerability in javax.servlet 3.1. Which of our Java apps use it?"

**Agent**:
1. `analyze_java_repos_from_uc()` - Analyze all Java repos
2. Query UC results:
   ```sql
   SELECT repo_name, summary.unique_packages
   FROM main.security.java_analysis_results
   WHERE array_contains(summary.unique_packages, 'javax.servlet');
   ```
3. For affected repos:
   - Show specific method usage
   - Estimate migration effort
   - Generate remediation plan

---

## 🚨 Limitations

1. **Syntax-only analysis**: No type resolution or compilation
2. **No cross-file analysis**: Each file analyzed independently
3. **Best-effort parsing**: Some complex Java might fail to parse
4. **Network required**: Must clone from Git every time

---

## 📚 Related Documentation

- `source_code_parser.py` - Original standalone Java parser
- `services/java_analyzer.py` - Refactored service class
- `models/java_analysis.py` - Pydantic data models
- `services/uc_integration.py` - UC read/write methods

---

## 🎯 Next Steps

1. ✅ Create UC tables (`java_repos_to_scan`, `java_analysis_results`)
2. ✅ Populate with repos to analyze
3. ✅ Deploy MCP server to Databricks Apps
4. ✅ Run analysis: `analyze_java_repos_from_uc()`
5. ✅ Query results for security insights

**Ready to analyze your Java codebase!** 🚀

