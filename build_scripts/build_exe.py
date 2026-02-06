"""
Automated build script for Sentinel-X executable.

Builds single-file Windows executable using PyInstaller.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def clean_build_artifacts():
    """Remove previous build artifacts."""
    print("[Build] Cleaning previous build artifacts...")
    
    artifacts = ['build', 'dist', '__pycache__']
    
    for artifact in artifacts:
        if os.path.exists(artifact):
            shutil.rmtree(artifact)
            print(f"  ✓ Removed: {artifact}")
    
    # Remove .spec file if exists (we use build_config/sentinelx.spec)
    if os.path.exists('sentinelx.spec'):
        os.remove('sentinelx.spec')
        print("  ✓ Removed: sentinelx.spec")


def verify_dependencies():
    """Verify all required dependencies are installed."""
    print("[Build] Verifying dependencies...")
    
    required = [
        'pyinstaller',
        'customtkinter',
        'fastapi',
        'uvicorn',
        'langchain',
        'chromadb',
    ]
    
    missing = []
    
    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✓ {package}")
        except ImportError:
            missing.append(package)
            print(f"  ✗ {package} (MISSING)")
    
    if missing:
        print(f"\n[Build] ✗ Missing dependencies: {', '.join(missing)}")
        print(f"[Build] Run: pip install {' '.join(missing)}")
        sys.exit(1)
    
    print("[Build] ✓ All dependencies found")


def build_executable():
    """Build executable using PyInstaller."""
    print("[Build] Building executable with PyInstaller...")
    
    spec_file = Path("build_config/sentinelx.spec")
    
    if not spec_file.exists():
        print(f"[Build] ✗ Spec file not found: {spec_file}")
        sys.exit(1)
    
    # Run PyInstaller
    cmd = [
        sys.executable,
        '-m', 'PyInstaller',
        '--clean',  # Clean cache
        '--noconfirm',  # Overwrite without asking
        str(spec_file)
    ]
    
    print(f"[Build] Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[Build] ✗ PyInstaller failed:")
        print(result.stderr)
        sys.exit(1)
    
    print("[Build] ✓ Executable built successfully")


def verify_build():
    """Verify build output exists and get file size."""
    print("[Build] Verifying build output...")
    
    exe_path = Path("dist/SentinelX.exe")
    
    if not exe_path.exists():
        print(f"[Build] ✗ Executable not found: {exe_path}")
        sys.exit(1)
    
    # Get file size
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    
    print(f"[Build] ✓ Executable found: {exe_path}")
    print(f"[Build] ✓ Size: {size_mb:.2f} MB")
    
    if size_mb > 150:
        print(f"[Build] ⚠ Warning: Executable larger than 150MB")
    
    return exe_path


def main():
    """Main build pipeline."""
    print("=" * 60)
    print("Sentinel-X Build Script v1.0")
    print("=" * 60)
    print()
    
    # Step 1: Clean
    clean_build_artifacts()
    print()
    
    # Step 2: Verify dependencies
    verify_dependencies()
    print()
    
    # Step 3: Build
    build_executable()
    print()
    
    # Step 4: Verify
    exe_path = verify_build()
    print()
    
    print("=" * 60)
    print("✓ BUILD SUCCESSFUL")
    print("=" * 60)
    print(f"\nExecutable location: {exe_path.absolute()}")
    print("\nNext steps:")
    print("1. Test executable: .\\dist\\SentinelX.exe")
    print("2. Create installer: python build_scripts\\build_installer.py")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[Build] ✗ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[Build] ✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
