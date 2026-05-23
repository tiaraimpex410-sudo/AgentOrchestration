import os
import sys
import tempfile
import time
import subprocess
import pytest
from src.cli.validate_release import validate_ref

def run_git(args, cwd):
    result = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

@pytest.fixture
def temp_git_repo():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize Git repo
        run_git(["init", "-b", "main"], cwd=temp_dir)
        run_git(["config", "user.name", "Test User"], cwd=temp_dir)
        run_git(["config", "user.email", "test@example.com"], cwd=temp_dir)
        
        # Create a dummy file and commit
        dummy_file = os.path.join(temp_dir, "dummy.txt")
        with open(dummy_file, "w") as f:
            f.write("hello")
        
        run_git(["add", "dummy.txt"], cwd=temp_dir)
        run_git(["commit", "-m", "Initial commit"], cwd=temp_dir)
        
        # Get head commit SHA
        _, commit_sha, _ = run_git(["rev-parse", "HEAD"], cwd=temp_dir)
        
        yield temp_dir, commit_sha

def test_validate_protected_branches(temp_git_repo):
    repo_dir, _ = temp_git_repo
    
    # Test refs/heads/main
    assert validate_ref("refs/heads/main", "workflow_dispatch", cwd=repo_dir) is True
    
    # Test refs/heads/develop
    assert validate_ref("refs/heads/develop", "workflow_dispatch", cwd=repo_dir) is True

def test_validate_unprotected_branch(temp_git_repo):
    repo_dir, _ = temp_git_repo
    
    # Test refs/heads/feature/test
    assert validate_ref("refs/heads/feature/test", "workflow_dispatch", cwd=repo_dir) is False

def test_validate_lightweight_tag(temp_git_repo):
    repo_dir, commit_sha = temp_git_repo
    
    # Create lightweight tag
    run_git(["tag", "v1.0.0-lightweight", commit_sha], cwd=repo_dir)
    
    assert validate_ref("refs/tags/v1.0.0-lightweight", "release", cwd=repo_dir) is False

def test_validate_unsigned_annotated_tag(temp_git_repo):
    repo_dir, commit_sha = temp_git_repo
    
    # Create unsigned annotated tag
    run_git(["tag", "-a", "v1.0.0-unsigned", "-m", "Unsigned release"], cwd=repo_dir)
    
    assert validate_ref("refs/tags/v1.0.0-unsigned", "release", cwd=repo_dir) is False

def test_validate_signed_tag(temp_git_repo):
    repo_dir, commit_sha = temp_git_repo
    
    # Manually construct a tag object with a PGP signature block to simulate a signed tag without needing GPG
    # Ensure all line endings are strictly LF (\n) as required by Git database objects
    tag_lines = [
        f"object {commit_sha}",
        "type commit",
        "tag v1.0.0-signed",
        f"tagger Test Tagger <tagger@example.com> {int(time.time())} +0000",
        "",
        "Mock signed tag message",
        "-----BEGIN PGP SIGNATURE-----",
        "Version: GnuPG v2",
        "Comment: Mock signature for testing",
        "",
        "mQINBFT3t74BEADKmocksignaturedata",
        "-----END PGP SIGNATURE-----",
        ""
    ]
    tag_data = "\n".join(tag_lines)
    
    # Use git mktag to write tag object to database as binary to avoid Windows text/newline translation
    proc = subprocess.run(["git", "mktag"], input=tag_data.encode("utf-8"), capture_output=True, cwd=repo_dir)
    assert proc.returncode == 0
    tag_sha = proc.stdout.decode("utf-8").strip()
    
    # Point the ref refs/tags/v1.0.0-signed to our new tag object
    code, _, err = run_git(["update-ref", "refs/tags/v1.0.0-signed", tag_sha], cwd=repo_dir)
    assert code == 0
    
    assert validate_ref("refs/tags/v1.0.0-signed", "release", cwd=repo_dir) is True
