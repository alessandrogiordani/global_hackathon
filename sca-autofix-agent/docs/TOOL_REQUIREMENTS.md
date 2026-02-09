# MCP Tool Requirements Analysis

Breakdown of which tools are **required** vs **optional** for different use cases.

---

## 🎯 For Library Migration Agent (Your Current Focus)

### ✅ **REQUIRED Tools (4 tools)**

1. **`get_library_migration_analysis`** ⭐ **ESSENTIAL**
   - Core tool for migration analysis
   - Returns breaking changes + source context
   - **Cannot be removed**

2. **`write_migration_analysis_to_uc`** ⭐ **ESSENTIAL**
   - Writes results back to UC
   - **Cannot be removed**

3. **`get_sca_findings_from_uc`** ✅ **REQUIRED**
   - Reads repos from UC table
   - Agent needs this to get repo list
   - **Keep**

4. **`record_user_decision_to_uc`** ✅ **REQUIRED**
   - Records user decisions
   - Audit trail requirement
   - **Keep**

---

### ❌ **NOT REQUIRED for Migration Workflow (15 tools)**

These tools are **not needed** for the library migration agent workflow:

#### **Python-Specific Tools (Not needed if only doing Java)**
5. `scan_repo_dependencies` - Python/JS/Java manifest scanning
6. `check_vulnerabilities` - OSV.dev vulnerability checking
7. `suggest_upgrades` - Python package upgrade suggestions
8. `analyze_package_usage` - Python AST analysis
9. `check_api_changes` - Python package API change detection
10. `fetch_and_analyze_changelog` - Python changelog analysis

#### **General Vulnerability Tools (Not needed if UC already has findings)**
11. `get_vulnerability_details` - CVE details lookup
12. `monitor_repo_security` - Continuous monitoring setup

#### **Patch Management Tools (Agent handles this with LLM)**
13. `generate_patch_preview` - Visual diff generation
14. `apply_security_patches` - Apply patches to repo
15. `validate_patch_with_tests` - Test patch validation

#### **Java Analysis Tools (Different use case)**
16. `analyze_java_repos_from_uc` - General Java code analysis (not migration-specific)

#### **Git Management (Optional - agent might not need)**
17. `clone_github_repo` - Clone to /Repos/ (migration tool uses temp clone)

#### **Diagnostics (Development only)**
18. `list_directory_contents` - Debugging tool

#### **UC Tools (Redundant)**
19. `write_analysis_to_uc` - Generic analysis write (migration has specific tool)

---

## 📊 Summary Table

| Tool | Required for Migration? | Why |
|------|------------------------|-----|
| `get_library_migration_analysis` | ✅ **YES** | Core migration analysis |
| `write_migration_analysis_to_uc` | ✅ **YES** | Write results |
| `get_sca_findings_from_uc` | ✅ **YES** | Read repos from UC |
| `record_user_decision_to_uc` | ✅ **YES** | Audit trail |
| `scan_repo_dependencies` | ❌ No | Python/JS focused |
| `check_vulnerabilities` | ❌ No | UC already has findings |
| `suggest_upgrades` | ❌ No | Python focused |
| `get_vulnerability_details` | ❌ No | Not needed for migration |
| `monitor_repo_security` | ❌ No | Different workflow |
| `list_directory_contents` | ❌ No | Debugging only |
| `analyze_package_usage` | ❌ No | Python focused |
| `check_api_changes` | ❌ No | Python focused |
| `fetch_and_analyze_changelog` | ❌ No | Python focused |
| `generate_patch_preview` | ❌ No | Agent generates patches |
| `apply_security_patches` | ❌ No | Agent handles this |
| `validate_patch_with_tests` | ❌ No | Different workflow |
| `clone_github_repo` | ❌ No | Migration uses temp clone |
| `analyze_java_repos_from_uc` | ❌ No | Different use case |
| `write_analysis_to_uc` | ❌ No | Use migration-specific tool |

---

## 🎯 Minimal MCP Server for Migration Agent

If you want to create a **minimal MCP server** with only migration tools:

### **Keep (4 tools):**
1. `get_library_migration_analysis`
2. `write_migration_analysis_to_uc`
3. `get_sca_findings_from_uc`
4. `record_user_decision_to_uc`

### **Remove (15 tools):**
All others can be removed if you're **only** doing library migration.

---

## 💡 Recommendation

### **Option A: Keep All Tools (Recommended)**
- ✅ **Flexibility**: Support multiple workflows
- ✅ **Future-proof**: Can add Python migration later
- ✅ **Reusability**: Tools useful for other agents
- ❌ **Larger codebase**: More to maintain

### **Option B: Minimal Server (Migration Only)**
- ✅ **Focused**: Only what's needed
- ✅ **Simpler**: Easier to understand
- ✅ **Faster**: Less code to load
- ❌ **Less flexible**: Can't support other workflows

---

## 🔍 Tool Dependencies

### **Tools that depend on others:**

- `suggest_upgrades` → uses `check_vulnerabilities` + `check_api_changes`
- `monitor_repo_security` → uses `scan_repo_dependencies` + `check_vulnerabilities`
- `apply_security_patches` → uses `generate_patch_preview`
- `validate_patch_with_tests` → uses `apply_security_patches`

**If you remove a tool, check if others depend on it!**

---

## ✅ Final Answer

**For Library Migration Agent, you only need 4 tools:**
1. `get_library_migration_analysis` ⭐
2. `write_migration_analysis_to_uc` ⭐
3. `get_sca_findings_from_uc`
4. `record_user_decision_to_uc`

**The other 15 tools are NOT required** for the migration workflow, but they're useful for:
- General vulnerability scanning
- Python package analysis
- Patch management workflows
- Other use cases

**Recommendation:** Keep all tools for flexibility, but know that only 4 are essential for your migration agent! 🎯

