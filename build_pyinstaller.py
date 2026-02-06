import os
import subprocess
import sys

def build():
    print("🚀 Starting Sentinel-X Build Process...")
    
    # 1. Install PyInstaller if missing
    try:
        import PyInstaller
    except ImportError:
        print("📦 Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        
    # 1.5 Generate icon if missing
    if not os.path.exists("assets/icon.ico"):
        print("🎨 Generating default icon...")
        try:
            from PIL import Image, ImageDraw
            target_dir = "assets"
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            
            img = Image.new('RGB', (256, 256), color = (73, 109, 137))
            d = ImageDraw.Draw(img)
            d.text((10,10), "SX", fill=(255,255,0))
            img.save("assets/icon.ico")
            print("✅ Icon created at assets/icon.ico")
        except ImportError:
            print("⚠️ PIL not installed, skipping icon generation. Build might warn.")
            # Create empty file or just skip
            pass
        except Exception as e:
            print(f"⚠️ Failed to create icon: {e}")

    # 2. Clean previous build
    if os.path.exists("dist"):
        import shutil
        print("🧹 Cleaning dist/ folder...")
        shutil.rmtree("dist")
    if os.path.exists("build"):
        import shutil
        print("🧹 Cleaning build/ folder...")
        shutil.rmtree("build")

    # 3. Run PyInstaller
    print("🔨 Building Executable...")
    try:
        subprocess.check_call([sys.executable, "-m", "PyInstaller", "SentinelX.spec", "--noconfirm"])
        print("✅ Build Complete!")
        print(f"📂 Output: {os.path.abspath('dist/SentinelX.exe')}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Build Failed: {e}")

if __name__ == "__main__":
    build()
