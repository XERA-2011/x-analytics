import argparse
import subprocess
import sys
import os

def run_command(command, description):
    print(f"👉 {description}...")
    try:
        # split command string into list for subprocess
        cmd_list = command.split()
        result = subprocess.run(cmd_list, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Passed")
            return True
        else:
            print("❌ Failed")
            print(result.stdout)
            print(result.stderr)
            return False
    except FileNotFoundError:
        print(f"⚠️  Tool not found: {command.split()[0]}. Please install it.")
        return False

def main():
    parser = argparse.ArgumentParser(description="Code Sentinel - Quality Check")
    parser.add_argument("--quick", action="store_true", help="Run only fast checks (ruff)")
    parser.add_argument("--full", action="store_true", help="Run all checks (ruff + mypy)")
    parser.add_argument("--fix", action="store_true", help="Auto-fix issues where possible")
    
    args = parser.parse_args()
    
    # Define paths
    project_root = os.getcwd()
    python_paths = ["analytics", "server.py"] # Adjust based on project structure
    web_paths = ["web"]

    success = True
    
    # 1. Python Linting & Formatting (Ruff)
    ruff_cmd = "ruff check"
    if args.fix:
        ruff_cmd += " --fix"
    
    # Add paths
    ruff_cmd += " " + " ".join(python_paths)
    
    if not run_command(ruff_cmd, "Running Python Linter (Ruff)"):
        success = False
        
    if args.fix:
        run_command(f"ruff format {' '.join(python_paths)}", "Running Python Formatter (Ruff)")

    # 2. Python Type Checking (Mypy) - Only on Full run
    if args.full:
        for path in python_paths:
            if not run_command(f"mypy {path} --ignore-missing-imports", f"Running Type Checker (Mypy) on {path}"):
                success = False

    # 3. Web Formatting (Prettier) - If we assume npx is available
    if args.fix:
        print("👉 Running Web Formatter (Prettier)...")
        # Ensure web directory exists
        if os.path.exists("web"):
            subprocess.run(["npx", "prettier", "--write", "web/**/*.{html,css,js}"], shell=False)

    if not success:
        print("\n💥 Some checks failed. See output above.")
        sys.exit(1)
    else:
        print("\n✨ All systems operational. Code looks clean.")
        sys.exit(0)

if __name__ == "__main__":
    main()
