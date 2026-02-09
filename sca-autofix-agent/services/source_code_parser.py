"""
Clone a GitHub repository and analyze Java source files using javalang.
 
Outputs:
  - structure.json: basic structure per file (package, top-level types)
  - calls.jsonl: one JSON record per method invocation ("API call") found
 
javalang notes:
  - javalang.parse.parse(...) returns a CompilationUnit (AST root).
  - Input must be a complete Java compilation unit (a full .java file).
  - AST nodes support iteration and filtering by type.
"""
 
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
 
import javalang
 
 
DEFAULT_EXCLUDE_DIRS = {
    ".git", ".idea", ".vscode",
    "target", "build", "out",
    ".gradle", ".mvn",
    "node_modules"
}
 
JAVA_FILE_RE = re.compile(r".*\.java$", re.IGNORECASE)
 
 
def run(cmd: List[str], cwd: Optional[Path] = None) -> None:
    """Run a command and raise on failure."""
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)} (exit={proc.returncode})")
 
 
def clone_repo(repo_url: str, dest: Path, ref: Optional[str] = None, depth: int = 1) -> Path:
    """
    Clone repo_url into dest.
    If ref is provided, tries to checkout that ref (branch/tag/commit).
    """
    if dest.exists():
        shutil.rmtree(dest)
 
    cmd = ["git", "clone"]
    if depth and depth > 0:
        cmd += ["--depth", str(depth)]
    if ref:
        # If it's a branch/tag, this helps; if it's a commit hash it still clones default branch first
        cmd += ["--branch", ref, "--single-branch"]
    cmd += [repo_url, str(dest)]
    try:
        run(cmd)
    except RuntimeError:
        # Fallback if --branch failed (e.g., ref is a commit hash)
        if ref:
            # clone default branch, then checkout
            run(["git", "clone"] + (["--depth", str(depth)] if depth and depth > 0 else []) + [repo_url, str(dest)])
            run(["git", "checkout", ref], cwd=dest)
        else:
            raise
    return dest
 
 
def iter_java_files(root: Path, exclude_dirs: set) -> List[Path]:
    """Return a list of .java files under root, skipping excluded directories."""
    java_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # in-place prune of excluded dirs
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for fn in filenames:
            if JAVA_FILE_RE.match(fn):
                java_files.append(Path(dirpath) / fn)
    return java_files
 
 
def safe_read_text(path: Path) -> str:
    """Read file content, tolerating unknown encodings."""
    # Most Java files are UTF-8; fall back to latin-1 if needed.
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="replace")
 
 
def node_position(node) -> Optional[Dict[str, int]]:
    """Extract best-effort position (line/column) from a javalang node."""
    pos = getattr(node, "position", None)
    if not pos:
        return None
    # javalang uses a (line, column) tuple-like object for some nodes
    try:
        return {"line": int(pos[0]), "column": int(pos[1])}
    except Exception:
        # Some versions expose .line/.column
        line = getattr(pos, "line", None)
        col = getattr(pos, "column", None)
        if line is not None and col is not None:
            return {"line": int(line), "column": int(col)}
    return None
 
 
def nearest_ancestor(path: Tuple, klass):
    """Find nearest ancestor of type `klass` in a (path, node) traversal path."""
    for anc in reversed(path):
        if isinstance(anc, klass):
            return anc
    return None
 
 
def extract_structure(compilation_unit) -> Dict[str, Any]:
    """Extract basic file structure from a CompilationUnit."""
    pkg = compilation_unit.package.name if compilation_unit.package else None
 
    # Top-level types: ClassDeclaration / InterfaceDeclaration / EnumDeclaration / AnnotationDeclaration
    top_types = []
    for t in compilation_unit.types or []:
        type_kind = t.__class__.__name__
        top_types.append({
            "name": getattr(t, "name", None),
            "kind": type_kind,
            "modifiers": sorted(list(getattr(t, "modifiers", []) or [])),
        })
 
    return {
        "package": pkg,
        "top_level_types": top_types,
    }
 
 
def invocation_record(file_path: str, path: Tuple, inv) -> Dict[str, Any]:
    """Build a JSON-serializable record for one MethodInvocation."""
    # MethodInvocation has fields like:
    # - member (method name)
    # - qualifier (e.g. System.out) OR None
    # - arguments (list of expressions)
    # - selectors (chained calls), sometimes
    member = getattr(inv, "member", None)
    qualifier = getattr(inv, "qualifier", None)
 
    # caller context
    cls = nearest_ancestor(path, javalang.tree.ClassDeclaration) \
          or nearest_ancestor(path, javalang.tree.InterfaceDeclaration) \
          or nearest_ancestor(path, javalang.tree.EnumDeclaration)
 
    mth = nearest_ancestor(path, javalang.tree.MethodDeclaration) \
          or nearest_ancestor(path, javalang.tree.ConstructorDeclaration)
 
    caller_class = getattr(cls, "name", None) if cls else None
    caller_method = getattr(mth, "name", None) if mth else None
    caller_method_kind = mth.__class__.__name__ if mth else None
 
    # args count
    args = getattr(inv, "arguments", None) or []
    arg_count = len(args)
 
    return {
        "file": file_path,
        "position": node_position(inv),
        "caller": {
            "class": caller_class,
            "method": caller_method,
            "method_kind": caller_method_kind,
        },
        "callee": {
            "qualifier": qualifier,     # best-effort (syntactic receiver/qualifier)
            "member": member,           # method name
            "arg_count": arg_count,
        }
    }
 
 
def analyze_java_file(java_file: Path) -> Dict[str, Any]:
    """Parse a .java file and return structure + invocations."""
    source = safe_read_text(java_file)
    try:
        tree = javalang.parse.parse(source)  # returns CompilationUnit
    except (javalang.parser.JavaSyntaxError, IndexError) as e:
        return {
            "file": str(java_file),
            "parse_ok": False,
            "error": f"{e.__class__.__name__}: {e}",
            "structure": None,
            "invocations": [],
        }
 
    structure = extract_structure(tree)
 
    invocations = []
    # Walk the AST and collect MethodInvocation nodes
    for path, node in tree:
        if isinstance(node, javalang.tree.MethodInvocation):
            invocations.append(invocation_record(str(java_file), path, node))
 
    return {
        "file": str(java_file),
        "parse_ok": True,
        "error": None,
        "structure": structure,
        "invocations": invocations,
    }
 
 
def main():
    ap = argparse.ArgumentParser(description="Clone a GitHub repo and parse Java files using javalang.")
    ap.add_argument("repo_url", help="GitHub repo URL, e.g. https://github.com/org/repo.git")
    ap.add_argument("--ref", default=None, help="Branch/tag/commit to checkout (optional).")
    ap.add_argument("--out", default="javalang_out", help="Output directory (default: javalang_out).")
    ap.add_argument("--depth", type=int, default=1, help="git clone depth (default: 1). Use 0 for full clone.")
    ap.add_argument("--exclude", action="append", default=[], help="Extra directory names to exclude (repeatable).")
    ap.add_argument("--keep-clone", action="store_true", help="Keep the cloned repo on disk (in output dir).")
    args = ap.parse_args()
 
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
 
    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    exclude_dirs.update(args.exclude)
 
    # Clone into a deterministic folder under output, or use temp dir
    clone_dir = out_dir / "repo"
    temp_root = None
    try:
        if not args.keep_clone:
            temp_root = tempfile.TemporaryDirectory()
            clone_dir = Path(temp_root.name) / "repo"
 
        print(f"[+] Cloning {args.repo_url} into {clone_dir}")
        clone_repo(args.repo_url, clone_dir, ref=args.ref, depth=args.depth)
 
        print("[+] Scanning for .java files...")
        java_files = iter_java_files(clone_dir, exclude_dirs)
        print(f"[+] Found {len(java_files)} Java files")
 
        structure_out = []
        calls_path = out_dir / "calls.jsonl"
        struct_path = out_dir / "structure.json"
 
        with calls_path.open("w", encoding="utf-8") as calls_f:
            for jf in java_files:
                result = analyze_java_file(jf)
                # Structure per file
                structure_out.append({
                    "file": result["file"],
                    "parse_ok": result["parse_ok"],
                    "error": result["error"],
                    "structure": result["structure"]
                })
 
                # Calls as JSON lines
                for call in result["invocations"]:
                    calls_f.write(json.dumps(call, ensure_ascii=False) + "\n")
 
        struct_path.write_text(json.dumps(structure_out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[✓] Wrote structure to: {struct_path}")
        print(f"[✓] Wrote calls (JSONL) to: {calls_path}")
 
        if args.keep_clone:
            # if keep_clone, ensure clone ends up in out_dir/repo
            if clone_dir != (out_dir / "repo"):
                # copy it
                dst = out_dir / "repo"
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(clone_dir, dst)
                print(f"[✓] Kept clone at: {dst}")
 
    finally:
        if temp_root is not None:
            temp_root.cleanup()
 