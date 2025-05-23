import subprocess
import os

def main():
    print("Building frontend...")
    # Determine the correct path to the frontend directory
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    build_script_path = os.path.join(frontend_dir, "build.sh")

    # Ensure the build script is executable
    try:
        # This might fail if the user doesn't have permissions, 
        # but it's good practice to try for convenience.
        os.chmod(build_script_path, 0o755) 
    except OSError as e:
        print(f"Could not make build.sh executable: {e}. Please ensure it has execute permissions.")
        # Depending on strictness, you might want to exit here if chmod fails.

    # Run the build script
    # Using shell=True can be a security risk if the path is constructed from user input,
    # but here it's from a fixed relative path.
    # For more robust error handling, check the return code.
    process = subprocess.run([build_script_path], cwd=frontend_dir, shell=False, check=False)
    if process.returncode != 0:
        print(f"Frontend build failed with exit code {process.returncode}.")
        print("Please check the output from the build script.")
        exit(1) # Exit if build fails
    print("Frontend built successfully.")

    print("Starting backend server with Uvicorn...")
    # Get the root directory of the project (knowledge_transfer_tool)
    project_root = os.path.dirname(__file__)
    # Run Uvicorn from the project root, pointing to the app instance within the backend package
    # The command becomes: uvicorn backend.main:app --host 0.0.0.0 --port 8000
    # We need to ensure that the 'backend' directory is in Python's path.
    # Running from project_root and using 'backend.main:app' should handle this if
    # the virtual environment (which has uvicorn) is activated.
    subprocess.run(
        ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=project_root,  # Run Uvicorn from the project's root directory
        check=True
    )

if __name__ == "__main__":
    main() 