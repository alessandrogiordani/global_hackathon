# 🔄 Tool Execution Flow Diagrams

Mermaid diagrams for presentations showing how the 15 MCP tools work together.

---

## 📊 Tool Organization (15 Tools)

```mermaid
graph TB
    subgraph Discovery["🔍 Discovery & Scanning (2)"]
        T1[scan_repo_dependencies]
        T2[list_directory_contents]
    end
    
    subgraph Vulnerability["🛡️ Vulnerability Analysis (2)"]
        T3[check_vulnerabilities]
        T4[monitor_repo_security]
    end
    
    subgraph CodeImpact["🔬 Code Impact Analysis (3)"]
        T5[analyze_package_usage]
        T6[check_api_changes]
        T7[fetch_and_analyze_changelog]
    end
    
    subgraph Patch["🔧 Patch Generation & Validation (3)"]
        T8[generate_patch_preview]
        T9[apply_security_patches]
        T10[validate_patch_with_tests]
    end
    
    subgraph UC["🗄️ Unity Catalog Integration (3)"]
        T11[get_sca_findings_from_uc]
        T12[write_analysis_to_uc]
        T13[record_user_decision_to_uc]
    end
    
    subgraph Util["📊 Utilities (2)"]
        T14[get_vulnerability_details]
        T15[suggest_upgrades]
    end
    
    style Discovery fill:#e1f5ff
    style Vulnerability fill:#fff4e1
    style CodeImpact fill:#f0e1ff
    style Patch fill:#e1ffe1
    style UC fill:#ffe1f0
    style Util fill:#f5f5f5
```

---

## 1️⃣ Quick Security Scan (3-5 tool calls)

**Use case:** User wants a fast overview of vulnerabilities

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant T1 as scan_repo_dependencies
    participant T3 as check_vulnerabilities
    participant OSV as OSV.dev API
    
    User->>Agent: "Check /Workspace/my-project for vulnerabilities"
    
    Agent->>T1: scan_repo_dependencies(repo_path)
    T1->>T1: Parse requirements.txt, pyproject.toml, etc.
    T1-->>Agent: Found 12 packages
    
    Agent->>T3: check_vulnerabilities(packages)
    T3->>OSV: Query CVEs for each package
    OSV-->>T3: 2 vulnerabilities found
    T3-->>Agent: requests (HIGH), urllib3 (MEDIUM)
    
    Agent-->>User: "Found 2 vulnerabilities:<br/>• requests 2.28.0 → CVE-2023-32681 (HIGH)<br/>• urllib3 1.26.0 → CVE-2021-33503 (MEDIUM)<br/>Would you like me to analyze code impact?"
    
    Note over User,Agent: ⏱️ Takes 5-15 seconds
```

---

## 2️⃣ Deep Analysis with Breaking Change Detection (6-10 tool calls)

**Use case:** User wants to understand upgrade impact before making changes

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant T1 as scan_repo_dependencies
    participant T3 as check_vulnerabilities
    participant T5 as analyze_package_usage
    participant T6 as check_api_changes
    participant T7 as fetch_and_analyze_changelog
    
    User->>Agent: "Analyze impact of upgrading pandas"
    
    Agent->>T1: scan_repo_dependencies(repo_path)
    T1-->>Agent: pandas 1.5.3 found
    
    Agent->>T3: check_vulnerabilities({pandas: 1.5.3})
    T3-->>Agent: 1 vulnerability → upgrade to 2.0.0
    
    Agent->>T5: analyze_package_usage(repo_path, "pandas")
    T5->>T5: Parse Python AST
    T5-->>Agent: Used in 5 files<br/>Methods: DataFrame.append, read_csv, concat
    
    Agent->>T6: check_api_changes("pandas", "1.5.3", "2.0.0", methods)
    T6->>T6: Check curated database
    T6-->>Agent: Breaking change: DataFrame.append removed
    
    alt More details needed
        Agent->>T7: fetch_and_analyze_changelog("pandas", "1.5.3", "2.0.0")
        T7->>T7: Fetch from GitHub Releases
        T7-->>Agent: Detailed migration guide
    end
    
    Agent-->>User: "📊 Impact Analysis:<br/>✅ No breaking changes in your code<br/>📁 Used in 5 files (23 call sites)<br/>🎯 Confidence: 95%<br/>Would you like to see the patch preview?"
    
    Note over User,Agent: ⏱️ Takes 30-60 seconds
```

---

## 3️⃣ Full Remediation with Testing (10-15 tool calls)

**Use case:** User wants end-to-end vulnerability fixing with validation

```mermaid
sequenceDiagram
    participant User
    participant Agent
    participant T1 as scan_repo
    participant T3 as check_vulns
    participant T5 as analyze_usage
    participant T6 as check_api
    participant T8 as generate_patch
    participant T9 as apply_patches
    participant T10 as validate_tests
    participant Git as Databricks Repos
    
    User->>Agent: "Fix all vulnerabilities and test"
    
    rect rgb(230, 240, 255)
        Note over Agent,T3: Phase 1: Discovery
        Agent->>T1: scan_repo_dependencies(repo_path)
        T1-->>Agent: 12 packages
        Agent->>T3: check_vulnerabilities(packages)
        T3-->>Agent: 3 vulnerable packages
    end
    
    rect rgb(255, 240, 230)
        Note over Agent,T6: Phase 2: Impact Analysis
        loop For each vulnerable package
            Agent->>T5: analyze_package_usage(repo_path, package)
            T5-->>Agent: Usage details
            Agent->>T6: check_api_changes(package, old, new)
            T6-->>Agent: Breaking changes (if any)
        end
    end
    
    rect rgb(230, 255, 240)
        Note over Agent,T8: Phase 3: Preview
        Agent->>T8: generate_patch_preview(repo_path, upgrade_plan)
        T8-->>Agent: Visual diff
        Agent-->>User: "Here's what will change..."
        User-->>Agent: "Approved ✅"
    end
    
    rect rgb(255, 230, 240)
        Note over Agent,Git: Phase 4: Apply & Validate
        Agent->>T9: apply_security_patches(repo_path, upgrade_plan)
        T9->>Git: Create branch "security-patches-20260203"
        T9->>Git: Commit changes
        Git-->>T9: Success
        T9-->>Agent: Branch created
        
        Agent->>T10: validate_patch_with_tests(repo_path, branch)
        T10->>Git: Checkout test branch
        T10->>T10: Run pytest
        T10-->>Agent: All 47 tests passed ✅
    end
    
    Agent-->>User: "✅ Patches applied to branch<br/>✅ All tests passed<br/>Ready to merge to main!"
    
    Note over User,Agent: ⏱️ Takes 2-5 minutes
```

---

## 4️⃣ Production UC Workflow (15+ tool calls)

**Use case:** Automated vulnerability scanning across multiple repositories

```mermaid
sequenceDiagram
    participant Checkmarx as Checkmarx SCA
    participant UC as Unity Catalog
    participant Agent
    participant T11 as get_sca_findings
    participant T1 as scan_repo
    participant T5 as analyze_usage
    participant T6 as check_api
    participant T12 as write_analysis
    participant UI as Databricks App UI
    participant T13 as record_decision
    participant T9 as apply_patches
    participant T10 as validate_tests
    
    Checkmarx->>UC: Write vulnerabilities to UC table
    
    rect rgb(230, 240, 255)
        Note over Agent,T11: Phase 1: Data Retrieval
        Agent->>T11: get_sca_findings_from_uc(priority=1)
        UC->>T11: Return critical repos
        T11-->>Agent: 5 repos with vulnerabilities
    end
    
    rect rgb(255, 240, 230)
        Note over Agent,T12: Phase 2: Analysis (per repo)
        loop For each repo
            Agent->>T1: scan_repo_dependencies(repo_path)
            T1-->>Agent: Current state
            
            loop For each vulnerable package
                Agent->>T5: analyze_package_usage(repo_path, package)
                T5-->>Agent: Usage analysis
                Agent->>T6: check_api_changes(package, old, new)
                T6-->>Agent: Breaking changes
            end
            
            Agent->>T12: write_analysis_to_uc(repo_id, results)
            T12->>UC: Store analysis results
        end
    end
    
    rect rgb(230, 255, 240)
        Note over UI,T13: Phase 3: User Review
        UI->>UC: Display analysis results
        UC-->>UI: Show recommendations
        UI-->>User: Review in dashboard
        User->>UI: Approve fix for repo_001
        
        UI->>T13: record_user_decision_to_uc(repo_001, "approved")
        T13->>UC: Log decision for audit
    end
    
    rect rgb(255, 230, 240)
        Note over Agent,T10: Phase 4: Apply & Validate
        Agent->>T9: apply_security_patches(repo_path, upgrade_plan)
        T9-->>Agent: Branch created
        Agent->>T10: validate_patch_with_tests(repo_path, branch)
        T10-->>Agent: Tests passed ✅
    end
    
    Agent-->>UI: "Remediation complete"
    UI-->>User: Notification
    
    Note over Checkmarx,User: ⏱️ Automated, runs continuously
```

---

## 5️⃣ Tool Dependencies Map

Shows which tools depend on outputs from other tools:

```mermaid
graph LR
    T1[scan_repo_dependencies]
    T3[check_vulnerabilities]
    T5[analyze_package_usage]
    T6[check_api_changes]
    T8[generate_patch_preview]
    T9[apply_security_patches]
    T10[validate_patch_with_tests]
    T11[get_sca_findings_from_uc]
    T12[write_analysis_to_uc]
    T13[record_user_decision_to_uc]
    
    T1 -->|packages| T3
    T3 -->|vulnerabilities| T8
    T1 -->|packages| T5
    T5 -->|methods_used| T6
    T6 -->|breaking_changes| T8
    T8 -->|upgrade_plan| T9
    T9 -->|branch_name| T10
    
    T11 -->|repos| T1
    T1 -->|scan_results| T12
    T5 -->|usage_analysis| T12
    T6 -->|api_changes| T12
    T12 -->|analysis_id| T13
    
    style T1 fill:#e1f5ff
    style T3 fill:#fff4e1
    style T5 fill:#f0e1ff
    style T6 fill:#f0e1ff
    style T8 fill:#e1ffe1
    style T9 fill:#e1ffe1
    style T10 fill:#e1ffe1
    style T11 fill:#ffe1f0
    style T12 fill:#ffe1f0
    style T13 fill:#ffe1f0
```

---

## 6️⃣ Decision Tree: Which Tools to Use

```mermaid
graph TD
    Start[User Request] --> Q1{What does<br/>user want?}
    
    Q1 -->|Quick check| Flow1[Quick Scan Flow]
    Q1 -->|Understand impact| Flow2[Deep Analysis Flow]
    Q1 -->|Fix vulnerabilities| Flow3[Full Remediation Flow]
    Q1 -->|Production pipeline| Flow4[UC Workflow]
    
    Flow1 --> Step1["1. scan_repo_dependencies<br/>2. check_vulnerabilities"]
    
    Flow2 --> Step2["1. scan_repo_dependencies<br/>2. check_vulnerabilities<br/>3. analyze_package_usage<br/>4. check_api_changes<br/>5. fetch_and_analyze_changelog"]
    
    Flow3 --> Step3["1-5: Same as Deep Analysis<br/>6. generate_patch_preview<br/>7. apply_security_patches<br/>8. validate_patch_with_tests"]
    
    Flow4 --> Step4["1. get_sca_findings_from_uc<br/>2-5: Analysis per repo<br/>6. write_analysis_to_uc<br/>7. record_user_decision_to_uc<br/>8-9: Apply & validate"]
    
    Step1 --> End[Present Results]
    Step2 --> End
    Step3 --> End
    Step4 --> End
    
    style Start fill:#e1f5ff
    style Q1 fill:#fff4e1
    style Flow1 fill:#e1ffe1
    style Flow2 fill:#f0e1ff
    style Flow3 fill:#ffe1e1
    style Flow4 fill:#ffe1f0
    style End fill:#f5f5f5
```

---

## 7️⃣ Breaking Change Detection Strategy

```mermaid
graph TD
    Start[check_api_changes called] --> DB{Check<br/>Curated DB}
    
    DB -->|Found in DB| Return1[Return known<br/>breaking changes]
    DB -->|Not in DB| Major{Major version<br/>bump?}
    
    Major -->|Yes| Fetch[fetch_and_analyze_changelog]
    Major -->|No| NoBreak[No breaking changes<br/>expected]
    
    Fetch --> GitHub[Try GitHub Releases]
    GitHub -->|Success| Parse1[Parse changelog]
    GitHub -->|Fail| PyPI[Try PyPI]
    PyPI -->|Success| Parse2[Parse changelog]
    PyPI -->|Fail| File[Try common files<br/>CHANGELOG.md, etc.]
    File -->|Success| Parse3[Parse changelog]
    File -->|Fail| Heuristic[Use semantic<br/>versioning heuristic]
    
    Parse1 --> LLM[Extract breaking changes]
    Parse2 --> LLM
    Parse3 --> LLM
    Heuristic --> Return3[Flag as potentially<br/>breaking, low confidence]
    
    LLM --> Return2[Return detected<br/>breaking changes]
    
    Return1 --> End[Return to agent]
    Return2 --> End
    Return3 --> End
    NoBreak --> End
    
    style Start fill:#e1f5ff
    style DB fill:#fff4e1
    style Fetch fill:#f0e1ff
    style LLM fill:#ffe1f0
    style End fill:#e1ffe1
```

---

## 8️⃣ Data Flow Architecture

```mermaid
graph TB
    subgraph Input["📥 Input Sources"]
        Repo[Databricks Repo<br/>/Workspace/]
        UCTable[Unity Catalog<br/>sca_findings]
        User[User Request]
    end
    
    subgraph Tools["🔧 MCP Tools (15)"]
        Discovery["Discovery & Scanning"]
        Vuln["Vulnerability Analysis"]
        Code["Code Impact Analysis"]
        Patch["Patch Generation"]
        UCInt["UC Integration"]
    end
    
    subgraph External["🌐 External APIs"]
        OSV[OSV.dev<br/>Vulnerability DB]
        PyPI[PyPI JSON API]
        NPM[npm Registry]
        Maven[Maven Central]
        GitHub[GitHub Releases API]
    end
    
    subgraph Output["📤 Outputs"]
        Report[Vulnerability Report]
        Diff[Patch Preview]
        Branch[Git Branch]
        UCOut[UC Tables]
        Audit[Audit Trail]
    end
    
    Repo --> Discovery
    UCTable --> UCInt
    User --> Discovery
    
    Discovery --> Vuln
    Discovery --> Code
    Vuln --> Patch
    Code --> Patch
    
    Vuln --> OSV
    Code --> PyPI
    Code --> NPM
    Code --> Maven
    Code --> GitHub
    
    Vuln --> Report
    Code --> Report
    Patch --> Diff
    Patch --> Branch
    UCInt --> UCOut
    UCInt --> Audit
    
    style Input fill:#e1f5ff
    style Tools fill:#fff4e1
    style External fill:#f0e1ff
    style Output fill:#e1ffe1
```

---

## 🎨 Usage Tips for Presentations

### Rendering Mermaid Diagrams

**Option 1: Mermaid Live Editor**
- Go to https://mermaid.live/
- Paste any diagram code
- Export as PNG/SVG for slides

**Option 2: Markdown Renderers**
- GitHub automatically renders Mermaid
- VS Code with Mermaid extension
- Notion, Obsidian support Mermaid

**Option 3: PowerPoint/Keynote**
- Export diagrams as PNG from Mermaid Live
- Insert into slides

### Recommended Diagrams for Different Audiences

| Audience | Best Diagrams |
|----------|---------------|
| **Executives** | #1 (Tool Organization), #6 (Decision Tree) |
| **Developers** | #2 (Deep Analysis), #3 (Full Remediation), #7 (Breaking Change) |
| **DevOps/SRE** | #4 (UC Workflow), #8 (Data Flow) |
| **Security Teams** | #1 (Tool Organization), #4 (UC Workflow) |
| **Product Demos** | #2 (Deep Analysis), #3 (Full Remediation) |

### Color Coding

- 🔵 Blue (`#e1f5ff`): Discovery/Input
- 🟡 Yellow (`#fff4e1`): Analysis/Processing
- 🟣 Purple (`#f0e1ff`): Code Analysis
- 🟢 Green (`#e1ffe1`): Output/Success
- 🔴 Pink (`#ffe1f0`): Integration/Storage

---

**All diagrams are ready to use in your slides!** 📊✨

