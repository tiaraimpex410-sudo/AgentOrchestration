import os
import fnmatch
from pathlib import Path

# Resolve root path of the repository
ROOT_DIR = Path(__file__).parent.parent.resolve()
DOCKERIGNORE_PATH = ROOT_DIR / ".dockerignore"

def parse_dockerignore(filepath):
    """Parses .dockerignore into a clean list of active matching patterns."""
    patterns = []
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    return patterns

def is_ignored(relative_path, patterns):
    """Evaluates if a relative path matches any .dockerignore pattern."""
    path_parts = Path(relative_path).parts
    if not path_parts:
        return False
        
    for pattern in patterns:
        clean_pat = pattern.rstrip("/")
        is_dir_only = pattern.endswith("/")
        
        # Check if the root directory matches directory-only patterns
        if is_dir_only:
            if path_parts[0] == clean_pat:
                return True
        else:
            # 1. Direct match on relative path or basename using wildcards
            if fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(os.path.basename(relative_path), pattern):
                return True
            # 2. Ancestor match (e.g. pattern '.git' ignores '.git/config')
            if fnmatch.fnmatch(path_parts[0], clean_pat):
                return True
                
    return False

def test_dockerignore_exists():
    """Verify that the mandatory .dockerignore file is present in the repository root."""
    assert DOCKERIGNORE_PATH.exists(), ".dockerignore file is missing from repository root!"

def test_sensitive_files_are_excluded():
    """Ensure that all critical environment, credentials, logs, and caches are ignored."""
    patterns = parse_dockerignore(DOCKERIGNORE_PATH)
    assert len(patterns) > 0, "No active rules found in .dockerignore!"
    
    prohibited_files = [
        ".env",
        ".env.safe",
        ".env.local",
        ".env.production",
        "api.log",
        "error.log",
        "scratch/private_key.pem",
        "scratch/manifest.json",
        "debug/dump.log",
        ".git/config",
        ".github/workflows/ci.yml",
        "__pycache__/server.pyc",
        ".pytest_cache/v/cache/lastfailed",
        ".venv/bin/activate",
        "venv/lib/site-packages",
        "build/lib/api.py",
        "dist/sdk.tar.gz",
        ".vscode/settings.json",
        ".idea/workspace.xml"
    ]
    
    for file_path in prohibited_files:
        assert is_ignored(file_path, patterns), f"Security Hazard: Prohibited context file '{file_path}' is NOT excluded by .dockerignore!"

def test_source_files_are_included():
    """Ensure standard source files and configuration tools are NOT accidentally ignored."""
    patterns = parse_dockerignore(DOCKERIGNORE_PATH)
    
    essential_files = [
        "src/__init__.py",
        "src/agent/executor.py",
        "src/api/server.py",
        "src/orchestrator/engine.py",
        "pyproject.toml",
        "Makefile",
        "README.md",
        "tests/test_config.py"
    ]
    
    for file_path in essential_files:
        assert not is_ignored(file_path, patterns), f"Config Error: Essential file '{file_path}' is accidentally ignored by .dockerignore!"
