"""
Data models for vulnerability scanner.
"""

from .package import Package, PackageVersion, DependencyInfo, PackageEcosystem
from .vulnerability import (
    Vulnerability,
    VulnerabilitySeverity,
    VulnerabilityReport,
    UpgradePlan,
    UpgradeRecommendation,
    VulnerablePackage,
    PatchPreview,
    FileDiff,
)
from .usage import (
    ImportStatement,
    MethodUsage,
    PackageUsageAnalysis,
    APIChange,
    BreakingChangeReport,
)
from .java_analysis import (
    JavaMethodCall,
    JavaClassInfo,
    JavaFileStructure,
    JavaAnalysisResult,
    JavaRepoScanRequest,
)

__all__ = [
    "Package",
    "PackageVersion",
    "DependencyInfo",
    "PackageEcosystem",
    "Vulnerability",
    "VulnerabilitySeverity",
    "VulnerabilityReport",
    "VulnerablePackage",
    "UpgradePlan",
    "UpgradeRecommendation",
    "PatchPreview",
    "FileDiff",
    "ImportStatement",
    "MethodUsage",
    "PackageUsageAnalysis",
    "APIChange",
    "BreakingChangeReport",
    "JavaMethodCall",
    "JavaClassInfo",
    "JavaFileStructure",
    "JavaAnalysisResult",
    "JavaRepoScanRequest",
]

