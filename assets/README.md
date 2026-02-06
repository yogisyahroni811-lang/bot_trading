# Sentinel-X Assets Directory

This directory contains application assets:

- **icon.ico** - Application icon (256x256) for Windows executable
- **logo.png** - High-resolution logo for splash screen
- **tray_icon.ico** - System tray icon (16x16, 32x32)

## Creating Icons

To create `icon.ico` from PNG:

```bash
# Using ImageMagick
convert logo.png -resize 256x256 icon.ico

# Or use online tool: https://convertio.co/png-ico/
```

## Icon Requirements

- **Main Icon**: 256x256px, .ico format
- **Tray Icon**: 16x16px and 32x32px multi-resolution .ico
- **Format**: PNG source, ICO output for Windows

## Placeholder

For now, PyInstaller will build without icon. Add icon.ico here before production release.
