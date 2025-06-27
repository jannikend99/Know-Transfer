import subprocess
import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Run the Knowledge Transfer Tool')
    parser.add_argument('--https', action='store_true', help='Run with HTTPS (required for audio recording)')
    parser.add_argument('--port', type=int, default=8080, help='Port to run the server on (default: 8080)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    args = parser.parse_args()

    print("Building frontend...")
    # Determine the correct path to the frontend directory
    # Since run.py is now in the root directory, we need to go into knowledge_transfer_tool
    project_root = os.path.join(os.path.dirname(__file__), "knowledge_transfer_tool")
    frontend_dir = os.path.join(project_root, "frontend")
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
    
    # Prepare the uvicorn command - exclude venv to prevent restarts when packages are installed
    uvicorn_cmd = [
        "uvicorn", 
        "backend.main:app", 
        "--host", args.host, 
        "--port", str(args.port),
        "--reload",  # Enable auto-reload for development
        "--reload-exclude", "backend/venv/*"  # Exclude virtual environment
    ]
    
    if args.https:
        # For HTTPS in development, we'll use self-signed certificates
        # Note: This will generate browser warnings, but it's needed for microphone access
        print("Running with HTTPS (self-signed certificate)...")
        print("Note: Your browser will show a security warning. Click 'Advanced' and 'Proceed' to continue.")
        print("This is necessary for audio recording functionality.")
        
        # Generate self-signed certificate if it doesn't exist
        cert_dir = os.path.join(project_root, "certs")
        cert_file = os.path.join(cert_dir, "cert.pem")
        key_file = os.path.join(cert_dir, "key.pem")
        
        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            print("Generating self-signed certificate...")
            os.makedirs(cert_dir, exist_ok=True)
            
            # Generate self-signed certificate using openssl
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:4096", "-nodes",
                "-out", cert_file, "-keyout", key_file, "-days", "365",
                "-subj", "/C=US/ST=State/L=City/O=Organization/CN=localhost"
            ], check=True)
            print("Self-signed certificate generated.")
        
        uvicorn_cmd.extend(["--ssl-keyfile", key_file, "--ssl-certfile", cert_file])
        
        protocol = "https"
    else:
        protocol = "http"
        print("\n" + "="*60)
        print("⚠️  IMPORTANT: Audio recording requires HTTPS!")
        print("If you plan to use voice input, run with --https flag:")
        print(f"python run.py --https")
        print("="*60 + "\n")
    
    # Print access information
    print(f"\n🚀 Server starting at {protocol}://{args.host}:{args.port}")
    if args.host == '0.0.0.0':
        print(f"   Local access: {protocol}://localhost:{args.port}")
        print(f"   Network access: {protocol}://127.0.0.1:{args.port}")
    
    # Run Uvicorn from the knowledge_transfer_tool directory
    try:
        subprocess.run(uvicorn_cmd, cwd=project_root, check=True)
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except subprocess.CalledProcessError as e:
        print(f"Server failed to start: {e}")
        if args.https and "openssl" in str(e):
            print("OpenSSL is required for HTTPS. Please install it or run without --https flag.")
        sys.exit(1)

if __name__ == "__main__":
    main() 