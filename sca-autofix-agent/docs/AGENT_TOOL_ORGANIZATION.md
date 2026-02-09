# Agent Tool Organization - Reducing Confusion

## 🚨 The Problem

**19 tools can confuse agents** because:
- Too many options to choose from
- Similar-sounding tools (e.g., `write_analysis_to_uc` vs `write_migration_analysis_to_uc`)
- Tools for different use cases mixed together
- Agent might pick wrong tool for the task

---

## ✅ Solutions

### **Solution 1: Clear Tool Naming with Prefixes**

Add prefixes to make tool purpose obvious:

**Current (Confusing):**
- `write_analysis_to_uc` - Generic, unclear
- `analyze_package_usage` - Python? Java? Unclear

**Better (Clear):**
- `migration_get_analysis` - Obviously for migration
- `migration_write_results` - Obviously for migration
- `python_analyze_usage` - Obviously for Python
- `java_analyze_repos` - Obviously for Java

**Recommendation:** Add `migration_` prefix to migration-specific tools

---

### **Solution 2: Enhanced Tool Descriptions**

Add clear "Use Case" and "When NOT to use" sections:

```python
@mcp_server.tool
def get_library_migration_analysis(...):
    """
    ⭐ PRIMARY TOOL FOR LIBRARY MIGRATION WORKFLOW
    
    Analyze library migration and return breaking changes with source code context.
    
    **USE CASE:**
    - When migrating Java libraries (e.g., Spring Boot 2.7 → 3.0)
    - When you need breaking changes + source context for LLM code generation
    - When analyzing library version upgrades
    
    **WHEN TO USE:**
    - ✅ Analyzing Java library migrations
    - ✅ Need breaking changes for specific library versions
    - ✅ Preparing data for LLM code generation
    
    **WHEN NOT TO USE:**
    - ❌ General vulnerability scanning (use check_vulnerabilities)
    - ❌ Python package analysis (use analyze_package_usage)
    - ❌ General Java code analysis (use analyze_java_repos_from_uc)
    
    **AGENT WORKFLOW:**
    1. Call this tool to get breaking_changes[]
    2. Use LLM to generate patches from breaking_changes
    3. Call write_migration_analysis_to_uc() to save results
    
    ...
    """
```

---

### **Solution 3: Tool Categories in System Prompt**

Guide the agent with clear categories in system prompt:

```python
system_prompt = """
You are a Java library migration expert.

## Available Tools (Organized by Use Case)

### 🎯 LIBRARY MIGRATION (Use These for Migration Tasks)
1. **get_library_migration_analysis** - ⭐ START HERE for migration
   - Returns breaking changes + source context
   - Use when: Analyzing library version upgrades
   
2. **write_migration_analysis_to_uc** - Write migration results
   - Use after: Generating patches with LLM

### 📊 DATA SOURCES (Use These to Get Input)
3. **get_sca_findings_from_uc** - Read repos from UC
   - Use when: Need list of repos to analyze

4. **record_user_decision_to_uc** - Record user decisions
   - Use when: User approves/rejects migration

### ⚠️ DO NOT USE FOR MIGRATION (These are for other workflows)
- analyze_package_usage (Python only)
- check_vulnerabilities (General scanning)
- scan_repo_dependencies (Python/JS manifests)
- ... (other tools not relevant to migration)

## Your Workflow:
1. get_sca_findings_from_uc() → Get repos
2. get_library_migration_analysis() → Get breaking changes
3. [Use LLM to generate patches]
4. write_migration_analysis_to_uc() → Save results
"""
```

---

### **Solution 4: Tool Metadata/Tags**

Add metadata to help agents filter (if MCP supports it):

```python
@mcp_server.tool
def get_library_migration_analysis(...):
    """
    ...
    """
    # Tool metadata (if supported)
    tool_metadata = {
        "category": "migration",
        "primary_use_case": "library_migration",
        "language": "java",
        "workflow_step": "analysis",
        "related_tools": ["write_migration_analysis_to_uc"]
    }
```

---

### **Solution 5: Rename Tools for Clarity**

Rename tools to make purpose obvious:

| Current Name | Better Name | Why |
|-------------|-------------|-----|
| `write_analysis_to_uc` | `python_write_analysis_to_uc` | Clarifies it's for Python |
| `analyze_package_usage` | `python_analyze_package_usage` | Clarifies it's for Python |
| `get_library_migration_analysis` | `migration_get_analysis` | Shorter, clearer |
| `write_migration_analysis_to_uc` | `migration_write_results` | Shorter, clearer |

---

## 🎯 Recommended Approach

### **Option A: Enhanced Descriptions (Easiest)**

Keep all tools but add clear "USE CASE" sections to descriptions:

```python
@mcp_server.tool
def get_library_migration_analysis(...):
    """
    ⭐ PRIMARY TOOL FOR JAVA LIBRARY MIGRATION
    
    Use this tool when:
    - Analyzing Java library version upgrades
    - Need breaking changes for migration planning
    - Preparing data for LLM code generation
    
    Do NOT use this tool for:
    - Python package analysis (use analyze_package_usage)
    - General vulnerability scanning (use check_vulnerabilities)
    - General Java code analysis (use analyze_java_repos_from_uc)
    
    ...
    """
```

### **Option B: Rename Tools (More Work, Better Clarity)**

Add prefixes to make purpose obvious:
- `migration_get_analysis`
- `migration_write_results`
- `python_analyze_usage`
- `java_analyze_repos`

### **Option C: System Prompt Filtering (Best for Agent)**

In agent system prompt, explicitly list which tools to use:

```python
# Agent system prompt
"""
For library migration tasks, ONLY use these 4 tools:
1. get_library_migration_analysis
2. write_migration_analysis_to_uc
3. get_sca_findings_from_uc
4. record_user_decision_to_uc

Ignore all other tools for migration workflow.
"""
```

---

## 📊 Tool Confusion Risk Assessment

| Tool | Confusion Risk | Why | Solution |
|------|---------------|-----|----------|
| `get_library_migration_analysis` | ✅ Low | Clear name, specific purpose | Add "PRIMARY TOOL" tag |
| `write_migration_analysis_to_uc` | ⚠️ Medium | Similar to `write_analysis_to_uc` | Rename or add clear distinction |
| `write_analysis_to_uc` | ⚠️ High | Generic name, might be confused with migration tool | Rename to `python_write_analysis_to_uc` |
| `analyze_package_usage` | ⚠️ High | Could be confused with migration analysis | Rename to `python_analyze_package_usage` |
| `check_api_changes` | ⚠️ Medium | Similar to migration analysis | Add "Python only" clarification |
| `analyze_java_repos_from_uc` | ⚠️ Medium | Similar name to migration tool | Add "General analysis, not migration" |

---

## ✅ Immediate Actions

### **1. Add Clear "USE CASE" Sections**

Update tool descriptions to include:
- ⭐ **PRIMARY TOOL** tags for migration tools
- **When to use** / **When NOT to use**
- **Related tools** section

### **2. Update System Prompt**

In agent configuration, explicitly guide tool selection:
- List migration tools first
- Mark other tools as "for other workflows"
- Provide clear workflow examples

### **3. Consider Renaming (Optional)**

If confusion persists, rename tools with prefixes:
- `migration_*` for migration tools
- `python_*` for Python tools
- `java_*` for Java tools

---

## 🎯 Best Practice: Tool Discovery

Agents typically:
1. Read tool names first
2. Read descriptions if name is unclear
3. Look for keywords matching their task

**Make it easy:**
- ✅ Clear, descriptive names
- ✅ "USE CASE" in first line of description
- ✅ "When NOT to use" section
- ✅ System prompt guidance

---

## 💡 Recommendation

**Start with Option A (Enhanced Descriptions)** - it's the easiest and most effective:

1. Add "⭐ PRIMARY TOOL" tags to migration tools
2. Add "USE CASE" sections to all tools
3. Update agent system prompt to list migration tools explicitly

This gives agents clear guidance without requiring code changes!

