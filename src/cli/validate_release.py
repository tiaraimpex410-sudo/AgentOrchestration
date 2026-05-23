import os
import sys
import subprocess

def run_git(args, cwd=None):
    result = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def validate_ref(ref, event_name, cwd=None):
    print(f"Validating ref: {ref}")
    print(f"Event name: {event_name}")

    is_protected = False

    if ref.startswith("refs/heads/"):
        branch_name = ref[len("refs/heads/"):]
        print(f"Branch Name: {branch_name}")
        if branch_name in ["main", "develop"]:
            print(f"Protected branch {branch_name} accepted.")
            is_protected = True
        else:
            print(f"Error: Branch {branch_name} is not a protected branch (must be main or develop).")
            return False
    elif ref.startswith("refs/tags/"):
        tag_name = ref[len("refs/tags/"):]
        print(f"Tag Name: {tag_name}")

        # Verify tag object type
        code, tag_type, err = run_git(["cat-file", "-t", tag_name], cwd=cwd)
        if code != 0 or tag_type != "tag":
            print(f"Error: Ref {tag_name} is not an annotated tag object (lightweight tags are not allowed). Details: {err}")
            return False

        # Verify tag signature
        code, tag_content, err = run_git(["cat-file", "-p", tag_name], cwd=cwd)
        if code != 0:
            print(f"Error reading tag object: {err}")
            return False

        if "-----BEGIN PGP SIGNATURE-----" in tag_content or "-----BEGIN SSH SIGNATURE-----" in tag_content:
            print(f"Success: Signed release tag {tag_name} verified.")
            is_protected = True
        else:
            print(f"Error: Tag {tag_name} is not signed. Release tags must be signed.")
            return False
    else:
        print(f"Error: Unsupported ref context {ref}.")
        return False

    # Write to GITHUB_OUTPUT if present
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        val = "true" if is_protected else "false"
        try:
            with open(github_output, "a") as f:
                f.write(f"is_protected={val}\n")
            print(f"Successfully wrote is_protected={val} to GITHUB_OUTPUT")
        except Exception as e:
            print(f"Warning: Failed to write to GITHUB_OUTPUT: {e}")

    return is_protected

if __name__ == "__main__":
    ref = os.environ.get("GITHUB_REF")
    event_name = os.environ.get("GITHUB_EVENT_NAME")

    if not ref:
        print("Error: GITHUB_REF environment variable is not set.")
        sys.exit(1)

    success = validate_ref(ref, event_name)
    if not success:
        sys.exit(1)
    sys.exit(0)
