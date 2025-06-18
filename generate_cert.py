#!/usr/bin/env python3
"""
Certificate generation script for HTTPS development server.
This creates self-signed certificates needed for audio recording functionality.
"""

import os
import subprocess
import sys

def generate_certificate():
    """Generate self-signed certificate for local development."""
    
    # Create certs directory
    project_root = os.path.join(os.path.dirname(__file__), "knowledge_transfer_tool")
    cert_dir = os.path.join(project_root, "certs")
    os.makedirs(cert_dir, exist_ok=True)
    
    cert_file = os.path.join(cert_dir, "cert.pem")
    key_file = os.path.join(cert_dir, "key.pem")
    
    # Check if certificates already exist
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print("Certificates already exist!")
        print(f"Certificate: {cert_file}")
        print(f"Private key: {key_file}")
        
        response = input("Do you want to regenerate them? (y/N): ").lower()
        if response != 'y':
            print("Keeping existing certificates.")
            return
    
    print("Generating self-signed certificate for localhost...")
    
    try:
        # Generate self-signed certificate
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:4096", "-nodes",
            "-out", cert_file, "-keyout", key_file, "-days", "365",
            "-subj", "/C=US/ST=Dev/L=Localhost/O=KnowledgeTransfer/CN=localhost",
            "-addext", "subjectAltName=DNS:localhost,DNS:127.0.0.1,IP:127.0.0.1"
        ], check=True)
        
        print("✅ Certificate generated successfully!")
        print(f"📁 Certificate location: {cert_file}")
        print(f"🔑 Private key location: {key_file}")
        print("\n🚀 You can now run the server with HTTPS:")
        print("   python run.py --https")
        print("\n⚠️  Note: Your browser will show a security warning.")
        print("   Click 'Advanced' → 'Proceed to localhost (unsafe)' to continue.")
        print("   This is normal for self-signed certificates in development.")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating certificate: {e}")
        print("\n💡 Make sure OpenSSL is installed:")
        print("   • macOS: brew install openssl")
        print("   • Ubuntu/Debian: sudo apt install openssl")
        print("   • Windows: Download from https://slproweb.com/products/Win32OpenSSL.html")
        sys.exit(1)
        
    except FileNotFoundError:
        print("❌ OpenSSL not found!")
        print("\n💡 Please install OpenSSL:")
        print("   • macOS: brew install openssl")
        print("   • Ubuntu/Debian: sudo apt install openssl")
        print("   • Windows: Download from https://slproweb.com/products/Win32OpenSSL.html")
        sys.exit(1)

if __name__ == "__main__":
    print("🔒 Knowledge Transfer Tool - Certificate Generator")
    print("=" * 50)
    generate_certificate() 