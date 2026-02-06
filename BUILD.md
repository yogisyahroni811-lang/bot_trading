# Build Guide for Sentinel-X

## Prerequisites

```bash
# Install packaging dependencies
pip install pyinstaller
```

## Building Executable

### Option 1: Automated Build (Recommended)

```bash
python build_scripts\build_exe.py
```

This will:

1. Clean previous build artifacts
2. Verify all dependencies are installed
3. Build single-file executable with PyInstaller
4. Output to `dist\SentinelX.exe`

### Option 2: Manual Build

```bash
# Clean previous builds
rmdir /s /q build dist

# Build with PyInstaller
pyinstaller --clean --noconfirm build_config\sentinelx.spec
```

## Build Output

- **Executable**: `dist\SentinelX.exe` (single-file, ~80-120MB)
- **No dependencies required** - all bundled in executable

## Testing Build

```bash
# Run executable
.\dist\SentinelX.exe

# Check version
.\dist\SentinelX.exe --version
```

## Troubleshooting

### "No module named 'X'" error

- Missing dependency in spec file
- Add to `hiddenimports` in `build_config\sentinelx.spec`

### Executable crashes on startup

- Check console output: build with `console=True` in spec
- Review `_MEIxxxxxx\` temp directory logs

### Large file size (>150MB)

- Exclude unnecessary packages in spec file `excludes`
- Enable UPX compression (already enabled)

## Icon Requirement

Place `icon.ico` in `assets\` directory before building for branded executable.
