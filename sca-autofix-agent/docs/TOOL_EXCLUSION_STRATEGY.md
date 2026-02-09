# Tool Exclusion Strategy: Remove vs. Prompt Filtering

## 🤔 The Question

Should we:
1. **Remove** unnecessary tools from MCP server (delete code)
2. **Exclude via prompt** (keep tools, tell agent to ignore them)

---

## 📊 Comparison

| Aspect | Remove Tools | Exclude via Prompt |
|--------|--------------|-------------------|
| **Code Complexity** | ✅ Simpler (fewer tools) | ❌ More tools to maintain |
| **Agent Confusion** | ✅ Zero confusion (tools don't exist) | ⚠️ Agent might still see them |
| **Flexibility** | ❌ Can't support other workflows | ✅ Can support multiple workflows |
| **Future-Proofing** | ❌ Hard to add back later | ✅ Easy to enable/disable |
| **Testing** | ✅ Easier (fewer tools to test) | ⚠️ Need to test prompt effectiveness |
| **Maintenance** | ✅ Less code to maintain | ❌ More code to maintain |
| **Deployment** | ✅ Smaller server footprint | ❌ Larger server footprint |

---

## 🎯 Recommendation: **Hybrid Approach**

### **Phase 1: Prompt Exclusion (Start Here)** ✅

**Why:**
- ✅ Fast to implement (just update prompt)
- ✅ Keeps flexibility for future
- ✅ Easy to test and iterate
- ✅ Can support multiple agents with different needs

**Implementation:**
```python
# Agent system prompt
system_prompt = """
You are a Java library migration expert.

## Available Tools

### ⭐ MIGRATION TOOLS (Use These)
1. get_library_migration_analysis - PRIMARY TOOL
2. write_migration_analysis_to_uc
3. get_sca_findings_from_uc
4. record_user_decision_to_uc

### ⚠️ IGNORE THESE TOOLS (Not for Migration)
The following tools are available but NOT relevant for library migration:
- analyze_package_usage (Python only)
- check_api_changes (Python only)
- scan_repo_dependencies (Python/JS)
- write_analysis_to_uc (Python analysis)
- generate_patch_preview (Agent handles this)
- apply_security_patches (Different workflow)
- validate_patch_with_tests (Different workflow)
- check_vulnerabilities (UC already has findings)
- get_vulnerability_details (Not needed)
- monitor_repo_security (Different workflow)
- analyze_java_repos_from_uc (General analysis, not migration)
- clone_github_repo (Migration uses temp clone)
- list_directory_contents (Debugging only)
- suggest_upgrades (Python only)
- fetch_and_analyze_changelog (Python only)

**IMPORTANT:** For migration tasks, ONLY use the 4 migration tools listed above.
Do NOT use any other tools.
"""
```

**Test this first** - if agent consistently picks wrong tools, move to Phase 2.

---

### **Phase 2: Remove Tools (If Needed)**

**When to remove:**
- ❌ Agent consistently picks wrong tools despite prompt
- ❌ You're certain you'll never need other workflows
- ❌ Codebase maintenance is a concern
- ❌ Server size/performance matters

**What to remove:**
Keep only these 4 tools:
1. `get_library_migration_analysis`
2. `write_migration_analysis_to_uc`
3. `get_sca_findings_from_uc`
4. `record_user_decision_to_uc`

**How to remove:**
- Comment out or delete tool functions in `server/tools.py`
- Update `test_local.py` to reflect new count
- Update README

---

## 🧪 Testing Strategy

### **Test Prompt Exclusion First:**

```python
# Test agent with migration task
test_prompt = "Analyze Spring Boot migration from 2.7.0 to 3.0.0"

# Expected behavior:
# ✅ Agent calls: get_library_migration_analysis
# ❌ Agent does NOT call: analyze_package_usage, check_api_changes, etc.

# If agent picks wrong tool → strengthen prompt or remove tools
# If agent picks right tool → prompt exclusion works!
```

### **Metrics to Track:**
- Tool selection accuracy (% of times agent picks correct tool)
- Confusion rate (% of times agent picks wrong tool)
- Response time (more tools = slower tool selection)

---

## 💡 Best Practice: **Conditional Tool Exposure**

### **Option C: Dynamic Tool Filtering (Advanced)**

If MCP supports it, expose different tool sets to different agents:

```python
# In MCP server
def load_tools(mcp_server, agent_type="migration"):
    """Load tools based on agent type."""
    
    if agent_type == "migration":
        # Only migration tools
        register_migration_tools(mcp_server)
    elif agent_type == "python":
        # Only Python tools
        register_python_tools(mcp_server)
    else:
        # All tools
        register_all_tools(mcp_server)
```

**Benefits:**
- ✅ Agent only sees relevant tools
- ✅ No confusion
- ✅ Still flexible (can support multiple agents)

**Requires:** MCP server to support tool filtering (may not be available)

---

## 🎯 My Recommendation

### **Start with Prompt Exclusion** ✅

**Reasons:**
1. **Fast to implement** - Just update system prompt
2. **Easy to test** - See if agent follows instructions
3. **Flexible** - Can support other workflows later
4. **Reversible** - Can remove tools later if needed

**If prompt exclusion works:**
- ✅ Keep all tools
- ✅ Use prompt to guide agent
- ✅ Support multiple workflows

**If prompt exclusion fails:**
- ❌ Agent still picks wrong tools
- ❌ Move to Phase 2: Remove unnecessary tools
- ❌ Create minimal migration-only MCP server

---

## 📝 Implementation Plan

### **Step 1: Update Agent System Prompt** (Do This First)

```python
# In your agent configuration
MIGRATION_AGENT_PROMPT = """
You are a Java library migration expert.

## Tool Selection Rules

**For migration tasks, ONLY use these 4 tools:**
1. get_library_migration_analysis
2. write_migration_analysis_to_uc
3. get_sca_findings_from_uc
4. record_user_decision_to_uc

**DO NOT use these tools for migration:**
- analyze_package_usage (Python only)
- check_api_changes (Python only)
- write_analysis_to_uc (Use write_migration_analysis_to_uc instead)
- [list all other tools]

If you see a tool that's not in the 4 migration tools above, ignore it.
"""
```

### **Step 2: Test Agent Behavior**

Run tests to see if agent:
- ✅ Picks correct tools
- ❌ Gets confused by other tools

### **Step 3: Decide Based on Results**

**If agent follows prompt:**
- ✅ Keep all tools
- ✅ Use prompt exclusion

**If agent gets confused:**
- ❌ Remove unnecessary tools
- ❌ Create minimal server

---

## 🔍 How to Test

```python
# Test script
def test_agent_tool_selection():
    """Test if agent picks correct tools."""
    
    agent = create_migration_agent()
    
    # Test case 1: Migration task
    result = agent.invoke("Analyze Spring Boot migration 2.7 → 3.0")
    
    # Check which tools were called
    tools_called = result.get("tools_called", [])
    
    # Expected: Only migration tools
    expected = [
        "get_library_migration_analysis",
        "write_migration_analysis_to_uc"
    ]
    
    # Check for wrong tools
    wrong_tools = [
        "analyze_package_usage",
        "check_api_changes",
        "write_analysis_to_uc"
    ]
    
    if any(tool in tools_called for tool in wrong_tools):
        print("❌ Agent picked wrong tools - consider removing them")
        return False
    else:
        print("✅ Agent picked correct tools - prompt exclusion works!")
        return True
```

---

## ✅ Final Answer

**Start with prompt exclusion** because:
1. ✅ Fastest to implement
2. ✅ Most flexible
3. ✅ Easy to test
4. ✅ Can always remove tools later if needed

**Remove tools only if:**
- ❌ Prompt exclusion doesn't work
- ❌ Agent consistently gets confused
- ❌ You're certain you don't need other workflows

**Best of both worlds:** Use prompt exclusion now, keep option to remove tools later if needed.

