# MCP Tools for Agent Integration

This document defines the MCP tools that the agent needs. The agent will be created separately on the workspace and will call these tools.

---

## 🎯 Agent Requirements

The agent needs MCP tools that provide:

1. **Breaking change detection** (L1 vs L2 library comparison)
2. **Source code context** (where breaking changes are used)
3. **Structured data** (easy for agent to process)
4. **UC integration** (read/write results)

**The agent will:**
- Call MCP tools to get data
- Use LLM to generate code patches
- Call MCP tools to write results back

---

## 🔧 Required MCP Tools

### **Tool 1: `get_library_migration_analysis`**

**Purpose:** Analyze library migration and return breaking changes with source code context.

**Input:**
```python
{
    "source_repo_url": "https://github.com/mycompany/app.git",
    "library_name": "spring-boot",
    "current_version": "2.7.0",
    "target_version": "3.0.0",
    "library_repo_url": "https://github.com/spring-projects/spring-boot.git"  # Optional
}
```

**Output:**
```python
{
    "status": "success",
    "library": "spring-boot",
    "from_version": "2.7.0",
    "to_version": "3.0.0",
    
    "breaking_changes": [
        {
            "id": "bc_001",
            "class": "org.springframework.web.servlet.config.annotation.WebMvcConfigurer",
            "method": "addResourceHandlers",
            "change_type": "signature_changed",  # or "method_removed", "method_renamed", "parameter_changed"
            "old_signature": "void addResourceHandlers(ResourceHandlerRegistry registry)",
            "new_signature": "void addResourceHandlers(ResourceHandlerRegistry registry, ContentNegotiationManager manager)",
            "change_description": "Added ContentNegotiationManager parameter",
            
            "affected_locations": [
                {
                    "file": "src/main/java/com/example/config/WebConfig.java",
                    "line": 42,
                    "column": 1,
                    
                    "source_context": {
                        "target_line": "public void addResourceHandlers(ResourceHandlerRegistry registry) {",
                        "surrounding_context": """
                            @Configuration
                            @EnableWebMvc
                            public class WebConfig implements WebMvcConfigurer {
                                
                                @Override
                                public void addResourceHandlers(ResourceHandlerRegistry registry) {
                                    registry.addResourceHandler("/static/**")
                                            .addResourceLocations("classpath:/static/");
                                }
                        """,
                        "full_method": """
                            @Override
                            public void addResourceHandlers(ResourceHandlerRegistry registry) {
                                registry.addResourceHandler("/static/**")
                                        .addResourceLocations("classpath:/static/");
                            }
                        """,
                        "class_name": "WebConfig",
                        "package": "com.example.config",
                        "imports": [
                            "org.springframework.web.servlet.config.annotation.WebMvcConfigurer",
                            "org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry"
                        ],
                        "method_name": "addResourceHandlers",
                        "method_kind": "MethodDeclaration"
                    }
                }
            ]
        }
    ],
    
    "summary": {
        "breaking_changes_count": 12,
        "affected_files": 5,
        "affected_invocations": 23,
        "unique_classes_changed": 8,
        "unique_methods_changed": 12
    },
    
    "metadata": {
        "source_files_analyzed": 247,
        "library_files_analyzed": {
            "v1": 1523,
            "v2": 1642
        },
        "analysis_duration_seconds": 45.2
    }
}
```

**What agent does with this:**
- Iterates through `breaking_changes`
- For each `affected_location`, builds LLM prompt using `source_context`
- Calls LLM to generate patch
- Combines patches with breaking change info

---

### **Tool 2: `get_source_code_context`** (Optional - if agent needs more context)

**Purpose:** Get additional source code context for a specific file/line.

**Input:**
```python
{
    "source_repo_url": "https://github.com/mycompany/app.git",
    "file_path": "src/main/java/com/example/config/WebConfig.java",
    "line_number": 42,
    "context_lines": 10  # Lines before/after
}
```

**Output:**
```python
{
    "file_path": "src/main/java/com/example/config/WebConfig.java",
    "line_number": 42,
    "target_line": "public void addResourceHandlers(ResourceHandlerRegistry registry) {",
    "surrounding_context": "...",
    "full_class": "...",
    "full_method": "...",
    "imports": [...],
    "dependencies": [...]  # Other classes/methods used in this file
}
```

---

### **Tool 3: `write_migration_analysis_to_uc`**

**Purpose:** Write migration analysis results (breaking changes + agent-generated patches) to UC.

**Input:**
```python
{
    "repo_id": "repo_123",
    "library": "spring-boot",
    "from_version": "2.7.0",
    "to_version": "3.0.0",
    
    "breaking_changes": [...],  # From Tool 1
    
    "patches": [  # Generated by agent using LLM
        {
            "file": "src/main/java/com/example/config/WebConfig.java",
            "line": 42,
            "old_code": "public void addResourceHandlers(ResourceHandlerRegistry registry) {",
            "new_code": "public void addResourceHandlers(ResourceHandlerRegistry registry, ContentNegotiationManager manager) {",
            "confidence": "high",  # "high", "medium", "low"
            "explanation": "Added ContentNegotiationManager parameter to match new signature",
            "generated_by": "gpt-4",  # LLM model used
            "generation_timestamp": "2026-02-05T10:30:00Z"
        }
    ],
    
    "summary": {
        "breaking_changes_count": 12,
        "patches_generated": 12,
        "patches_high_confidence": 10,
        "patches_medium_confidence": 2,
        "patches_low_confidence": 0,
        "migration_complexity": "medium",  # "low", "medium", "high"
        "estimated_effort_hours": 2.5,
        "auto_fixable_percent": 85.0
    }
}
```

**Output:**
```python
{
    "status": "success",
    "analysis_id": "uuid-here",
    "message": "Analysis written to UC table"
}
```

---

### **Tool 4: `get_sca_findings_from_uc`** (Already exists)

**Purpose:** Read vulnerable repos from UC table.

**Input:**
```python
{
    "catalog": "ing_hackathon",
    "schema": "sca_advisor",
    "status": "ready",
    "priority": 1  # Optional
}
```

**Output:**
```python
{
    "repos": [
        {
            "repo_id": "repo_123",
            "repo_name": "customer-service",
            "repo_pointer": "https://github.com/mycompany/customer-service.git",
            "vuln_libs": [
                {
                    "library": "spring-boot",
                    "current_version": "2.7.0",
                    "cve_ids": ["CVE-2023-20883"],
                    "cvss_score": 7.5
                }
            ],
            "candidate_versions": ["2.7.14", "3.0.0"],
            "priority": 1,
            "status": "ready"
        }
    ],
    "total_repos": 5
}
```

---

### **Tool 5: `record_user_decision_to_uc`** (Already exists)

**Purpose:** Record user approval/rejection of migration.

**Input:**
```python
{
    "repo_id": "repo_123",
    "library": "spring-boot",
    "target_version": "3.0.0",
    "decision": "approved",  # or "rejected"
    "user_email": "user@company.com",
    "decision_reason": "User approved after reviewing patches"
}
```

---

## 📊 Data Flow

```
Agent Workflow:
┌─────────────────────────────────────────────────────────┐
│ 1. Agent calls: get_sca_findings_from_uc()          │
│    → Gets list of repos to analyze                      │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Agent calls: get_library_migration_analysis()        │
│    → Gets breaking_changes[] + source_context[]         │
│    → NO LLM in MCP, just structured data                │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Agent uses LLM (separate, not in MCP):               │
│    For each breaking_change:                            │
│      - Build prompt from breaking_change + source_context│
│      - Call LLM (GPT-4/Claude)                          │
│      - Get updated_code                                  │
│    → Generate patches[]                                  │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Agent calls: write_migration_analysis_to_uc()       │
│    → Writes breaking_changes + patches to UC            │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Streamlit app reads from UC and displays             │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Design Principles

### **MCP Tools Should:**
✅ Return structured data (dicts, lists)  
✅ Include all context needed for LLM  
✅ Be stateless (no session management)  
✅ Be fast (data extraction only)  
✅ Handle errors gracefully  

### **MCP Tools Should NOT:**
❌ Call LLM APIs  
❌ Generate code patches  
❌ Make decisions  
❌ Store state  

### **Agent Should:**
✅ Orchestrate tool calls  
✅ Use LLM for code generation  
✅ Make decisions  
✅ Handle state/context  

---

## 📝 Tool Implementation Checklist

### **Tool 1: `get_library_migration_analysis`**
- [ ] Clone source repo (temp)
- [ ] Clone library L1 (temp)
- [ ] Clone library L2 (temp)
- [ ] Parse source code with javalang
- [ ] Extract method invocations
- [ ] Parse library L1 declarations
- [ ] Parse library L2 declarations
- [ ] Diff L1 vs L2
- [ ] Cross-reference with source code
- [ ] Return structured breaking_changes + source_context
- [ ] Auto-cleanup temp repos

### **Tool 2: `get_source_code_context`** (Optional)
- [ ] Clone source repo (temp)
- [ ] Read specific file
- [ ] Extract context around line
- [ ] Return structured context
- [ ] Auto-cleanup

### **Tool 3: `write_migration_analysis_to_uc`**
- [ ] Validate input data
- [ ] Write to UC table
- [ ] Return analysis_id

### **Tool 4: `get_sca_findings_from_uc`** (Already exists ✅)
- [ ] Query UC table
- [ ] Return repos list

### **Tool 5: `record_user_decision_to_uc`** (Already exists ✅)
- [ ] Write decision to UC
- [ ] Return decision_id

---

## 🔍 Example Agent Code (For Reference)

```python
# This is what the agent (separate workspace) would do:

from databricks_mcp import MCPClient
from langchain_openai import ChatOpenAI

# Initialize
mcp = MCPClient(server_url="http://localhost:8000/mcp/v1")
llm = ChatOpenAI(model="gpt-4")

# Step 1: Get breaking changes from MCP
analysis = mcp.call_tool(
    "get_library_migration_analysis",
    source_repo_url="https://github.com/mycompany/app.git",
    library_name="spring-boot",
    current_version="2.7.0",
    target_version="3.0.0"
)

# Step 2: Generate patches with LLM (agent's job)
patches = []
for breaking_change in analysis["breaking_changes"]:
    for location in breaking_change["affected_locations"]:
        # Build prompt
        prompt = f"""
        Update this code for {breaking_change['library']} {breaking_change['from_version']} → {breaking_change['to_version']}:
        
        Change: {breaking_change['old_signature']} → {breaking_change['new_signature']}
        
        Current code:
        {location['source_context']['target_line']}
        
        Context:
        {location['source_context']['surrounding_context']}
        """
        
        # Call LLM (agent's responsibility)
        response = llm.invoke(prompt)
        patch = parse_llm_response(response)
        
        patches.append({
            "file": location["file"],
            "line": location["line"],
            "old_code": location["source_context"]["target_line"],
            "new_code": patch["updated_code"],
            "confidence": patch["confidence"]
        })

# Step 3: Write back via MCP
mcp.call_tool(
    "write_migration_analysis_to_uc",
    repo_id="repo_123",
    library="spring-boot",
    from_version="2.7.0",
    to_version="3.0.0",
    breaking_changes=analysis["breaking_changes"],
    patches=patches,
    summary=analysis["summary"]
)
```

---

## ✅ Summary

**MCP Server Provides:**
1. `get_library_migration_analysis` - Breaking changes + source context
2. `get_source_code_context` - Additional context (optional)
3. `write_migration_analysis_to_uc` - Write results
4. `get_sca_findings_from_uc` - Read repos (exists)
5. `record_user_decision_to_uc` - Record decisions (exists)

**Agent (You Create Separately) Provides:**
- LLM integration (GPT-4, Claude, etc.)
- Code generation logic
- Orchestration
- State management

**Clear separation of concerns!** 🎯

