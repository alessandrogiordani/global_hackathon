# LangGraph MCP Architecture (Correct Pattern)

Based on [Databricks LangGraph MCP Tool-Calling Agent](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/langgraph-mcp-tool-calling-agent.html), the LLM should be in the **agent layer**, not the MCP server.

---

## 🏗️ Correct Architecture

### **Separation of Concerns:**

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server                                │
│  (Data extraction, analysis, no LLM)                        │
│                                                              │
│  Tools:                                                     │
│  • analyze_library_migration()                              │
│    → Returns: breaking_changes + source_context             │
│    → NO LLM calls                                           │
│                                                              │
│  • get_breaking_changes()                                   │
│  • get_source_code_context()                               │
│  • write_analysis_to_uc()                                   │
└────────────────────┬────────────────────────────────────────┘
                     │ Returns structured data
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              LangGraph Agent                                 │
│  (Orchestration + LLM for code generation)                  │
│                                                              │
│  1. Calls MCP tool: analyze_library_migration()             │
│     → Receives: breaking_changes[], source_context[]         │
│                                                              │
│  2. For each breaking change:                               │
│     → Uses LLM (GPT-4/Claude) to generate patch             │
│     → LLM receives: breaking_change + source_context         │
│     → LLM returns: updated_code                              │
│                                                              │
│  3. Calls MCP tool: write_analysis_to_uc()                  │
│     → Writes: breaking_changes + generated_patches           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Refactored MCP Tool

### **Before (Wrong - LLM in MCP):**

```python
@mcp_server.tool
def analyze_library_migration(...):
    # ... clone repos, parse, diff ...
    
    # ❌ WRONG: LLM call inside MCP tool
    patches = []
    for breaking_change in breaking_changes:
        patch = llm_generator.generate_patch(...)  # LLM call here
        patches.append(patch)
    
    return {"patches": patches}  # Includes LLM-generated code
```

### **After (Correct - No LLM in MCP):**

```python
@mcp_server.tool
def analyze_library_migration(
    source_repo_url: str,
    library_name: str,
    current_version: str,
    target_version: str
) -> dict:
    """
    Analyze library migration and return breaking changes + source context.
    
    This tool does NOT generate patches - that's the agent's job.
    Returns structured data for the agent to use with LLM.
    """
    # 1. Clone repos (temp)
    # 2. Parse source code
    # 3. Parse library declarations
    # 4. Diff libraries
    # 5. Cross-reference with source code
    
    return {
        "status": "success",
        "library": library_name,
        "from_version": current_version,
        "to_version": target_version,
        
        # ✅ Structured data for agent
        "breaking_changes": [
            {
                "class": "org.springframework.web.servlet.config.annotation.WebMvcConfigurer",
                "method": "addResourceHandlers",
                "change_type": "signature_changed",
                "old_signature": "void addResourceHandlers(ResourceHandlerRegistry registry)",
                "new_signature": "void addResourceHandlers(ResourceHandlerRegistry registry, ContentNegotiationManager manager)",
                "affected_locations": [
                    {
                        "file": "WebConfig.java",
                        "line": 42,
                        "source_context": {
                            "target_line": "public void addResourceHandlers(ResourceHandlerRegistry registry) {",
                            "surrounding_context": "... 5 lines before/after ...",
                            "full_method": "...",
                            "class_name": "WebConfig",
                            "imports": [...]
                        }
                    }
                ]
            }
        ],
        
        "summary": {
            "breaking_changes_count": 12,
            "affected_files": 5,
            "affected_invocations": 23
        }
        
        # ❌ NO patches here - agent generates them
    }
```

---

## 🤖 LangGraph Agent Implementation

### **Agent with LLM for Code Generation:**

```python
# In Databricks notebook or separate service
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from databricks_mcp import MCPClient
import json

# Initialize MCP client
mcp_client = MCPClient(
    server_url="http://localhost:8000/mcp/v1",
    server_name="vulnerability-scanner"
)

# Initialize LLM
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.2
)

def analyze_migration_agent(user_request: dict) -> dict:
    """
    LangGraph agent that orchestrates migration analysis with LLM.
    
    Args:
        user_request: {
            "source_repo_url": str,
            "library_name": str,
            "current_version": str,
            "target_version": str
        }
    """
    
    # Step 1: Call MCP tool to get breaking changes
    analysis = mcp_client.call_tool(
        "analyze_library_migration",
        source_repo_url=user_request["source_repo_url"],
        library_name=user_request["library_name"],
        current_version=user_request["current_version"],
        target_version=user_request["target_version"]
    )
    
    breaking_changes = analysis["breaking_changes"]
    
    # Step 2: Use LLM to generate patches for each breaking change
    patches = []
    
    for breaking_change in breaking_changes:
        for location in breaking_change["affected_locations"]:
            # Build LLM prompt
            prompt = build_llm_prompt(breaking_change, location)
            
            # Call LLM (this is where LLM lives - in the agent!)
            response = llm.invoke([
                HumanMessage(content=prompt)
            ])
            
            # Parse LLM response
            patch = parse_llm_response(response.content, location)
            patches.append(patch)
    
    # Step 3: Write results back to UC via MCP tool
    mcp_client.call_tool(
        "write_analysis_to_uc",
        repo_id=user_request.get("repo_id"),
        library=user_request["library_name"],
        target_version=user_request["target_version"],
        breaking_changes=breaking_changes,
        patches=patches,
        summary=analysis["summary"]
    )
    
    return {
        "breaking_changes": breaking_changes,
        "patches": patches,
        "summary": analysis["summary"]
    }

def build_llm_prompt(breaking_change: dict, location: dict) -> str:
    """Build prompt for LLM to generate patch."""
    return f"""
You are updating Java code to migrate from {breaking_change['library']} {breaking_change['from_version']} to {breaking_change['to_version']}.

BREAKING CHANGE:
Method: {breaking_change['method']}
Old: {breaking_change['old_signature']}
New: {breaking_change['new_signature']}
Change Type: {breaking_change['change_type']}

CURRENT CODE:
File: {location['file']}
Line: {location['line']}

```java
{location['source_context']['surrounding_context']}
```

The problematic line is:
```java
{location['source_context']['target_line']}
```

TASK:
Generate the updated code that works with the new signature.
- Preserve functionality
- Make minimal changes
- Use idiomatic Java

Return JSON:
{{
  "updated_code": "...",
  "explanation": "...",
  "confidence": "high|medium|low"
}}
"""

def parse_llm_response(response: str, location: dict) -> dict:
    """Parse LLM response into patch structure."""
    try:
        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            patch_data = json.loads(json_match.group(0))
            
            return {
                "file": location["file"],
                "line": location["line"],
                "old_code": location["source_context"]["target_line"],
                "updated_code": patch_data["updated_code"],
                "explanation": patch_data.get("explanation", ""),
                "confidence": patch_data.get("confidence", "medium")
            }
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return {
            "file": location["file"],
            "line": location["line"],
            "updated_code": None,
            "error": str(e),
            "confidence": "low"
        }
```

---

## 📊 Complete Workflow

### **Step-by-Step:**

```
1. User selects repo + library + target version in Streamlit
   ↓
2. Streamlit calls LangGraph agent
   ↓
3. Agent calls MCP tool: analyze_library_migration()
   → MCP returns: breaking_changes[] + source_context[]
   → NO LLM calls in MCP
   ↓
4. Agent receives breaking changes
   ↓
5. For each breaking change:
   a. Agent builds LLM prompt (breaking_change + source_context)
   b. Agent calls LLM (GPT-4/Claude) ← LLM is HERE
   c. LLM returns: updated_code
   d. Agent parses LLM response
   ↓
6. Agent calls MCP tool: write_analysis_to_uc()
   → Writes: breaking_changes + patches (from LLM)
   ↓
7. Streamlit reads from UC and displays results
```

---

## 🎯 Key Differences

| Aspect | ❌ Wrong (LLM in MCP) | ✅ Correct (LLM in Agent) |
|--------|----------------------|---------------------------|
| **LLM Location** | Inside MCP tool | In LangGraph agent |
| **MCP Tool Returns** | Patches (LLM-generated) | Breaking changes + context |
| **Agent Role** | Just orchestrates | Orchestrates + generates code |
| **Separation** | Mixed concerns | Clear separation |
| **Flexibility** | Hard to change LLM | Easy to swap LLM models |
| **Cost Control** | LLM calls in MCP | LLM calls in agent (trackable) |

---

## 🔧 Updated MCP Tool Signature

### **New Tool: `get_migration_analysis` (No LLM)**

```python
@mcp_server.tool
def get_migration_analysis(
    source_repo_url: str,
    library_name: str,
    current_version: str,
    target_version: str,
    library_repo_url: str = None
) -> dict:
    """
    Analyze library migration and return breaking changes with source context.
    
    This tool does NOT generate code patches - that's the agent's responsibility.
    Returns structured data for the agent to use with LLM.
    
    Args:
        source_repo_url: Git URL of source code
        library_name: Library being upgraded
        current_version: Current version (L1)
        target_version: Target version (L2)
        library_repo_url: Optional GitHub URL of library
    
    Returns:
        dict: {
            "breaking_changes": [
                {
                    "class": str,
                    "method": str,
                    "change_type": str,
                    "old_signature": str,
                    "new_signature": str,
                    "affected_locations": [
                        {
                            "file": str,
                            "line": int,
                            "source_context": {
                                "target_line": str,
                                "surrounding_context": str,
                                "full_method": str,
                                "class_name": str,
                                "imports": list
                            }
                        }
                    ]
                }
            ],
            "summary": {
                "breaking_changes_count": int,
                "affected_files": int,
                "affected_invocations": int
            }
        }
    """
    # Implementation: clone, parse, diff, return structured data
    # NO LLM calls here!
```

---

## 📝 Updated Integration Guide

### **Streamlit → Agent → MCP → Agent (LLM) → MCP → UC**

```python
# In Streamlit app
def analyze_migration(repo_id, library, target_version):
    """Call LangGraph agent (not MCP directly)."""
    
    # Agent handles everything:
    # 1. Calls MCP for analysis
    # 2. Uses LLM for code generation
    # 3. Writes to UC
    
    agent = get_langgraph_agent()  # Initialize agent
    
    result = agent.invoke({
        "repo_id": repo_id,
        "library": library,
        "target_version": target_version
    })
    
    return result
```

---

## ✅ Benefits of This Architecture

1. **Clear Separation**: MCP = data, Agent = intelligence
2. **Flexible LLM**: Easy to swap models (GPT-4, Claude, Databricks FM)
3. **Cost Tracking**: LLM calls visible in agent layer
4. **Testability**: Can test MCP tools without LLM costs
5. **Scalability**: MCP tools are stateless, agent handles state
6. **Follows Databricks Pattern**: Matches official LangGraph MCP architecture

---

## 🚀 Next Steps

1. **Refactor `analyze_library_migration`** to remove LLM calls
2. **Create LangGraph agent** with LLM for code generation
3. **Update integration guide** to show agent pattern
4. **Test end-to-end** with LangGraph agent

This architecture aligns with the [Databricks LangGraph MCP documentation](https://docs.databricks.com/aws/en/notebooks/source/generative-ai/langgraph-mcp-tool-calling-agent.html)!

