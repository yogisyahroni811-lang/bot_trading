#!/usr/bin/env python3
"""
License Key Generator for Sentinel-X

Generates license keys for different tiers:
- TRIAL: 7 days, 50 trades
- PRO: Lifetime (no expiry), unlimited trades
- ENTERPRISE: Lifetime + white label + support

Usage:
    python tools/generate_license.py --trial
    python tools/generate_license.py --tier PRO
    python tools/generate_license.py --tier PRO --batch 1000
    python tools/generate_license.py --tier ENTERPRISE --batch 100
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.license_manager import LicenseManager


def generate_single_license(tier: str, directory: str, index: int = None):
    """
    Generate a single license key and save metadata.
    
    Args:
        tier: License tier (TRIAL, PRO, ENTERPRISE)
        directory: Directory to save license info
        index: Optional index untuk batch generation
        
    Returns:
        (license_key, file_path, metadata)
    """
    lm = LicenseManager()
    
    license_key = lm.generate_license_key(tier)
    license_data = lm.create_license_data(license_key, tier)
    
    os.makedirs(directory, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create filename dengan optional index
    if index is not None:
        base_name = f"{tier}_{index:04d}_{timestamp}"
    else:
        base_name = f"{tier}_{timestamp}"
    
    file_path = os.path.join(directory, f"{base_name}.json")
    
    metadata = {
        "license_key": license_key,
        "tier": tier,
        "generated_at": datetime.now().isoformat(),
        "hardware_id": lm.hardware_id,
        "expires_at": "Lifetime" if tier in ["PRO", "ENTERPRISE"] else "7 days from activation",
        "max_trades": 50 if tier == "TRIAL" else 0,
        "features": license_data["features"]
    }
    
    with open(file_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return license_key, file_path, metadata


def generate_batch_licenses(tier: str, count: int, directory: str):
    """
    Generate multiple license keys in batch.
    
    Args:
        tier: License tier (TRIAL, PRO, ENTERPRISE)
        count: Number of licenses to generate
        directory: Directory to save license info
        
    Returns:
        List of (license_key, file_path, metadata) tuples
    """
    print(f"\nGenerating {count} {tier} licenses...")
    print("=" * 60)
    
    results = []
    for i in range(1, count + 1):
        license_key, file_path, metadata = generate_single_license(tier, directory, i)
        results.append((license_key, file_path, metadata))
        
        # Progress indicator every 100 licenses
        if i % 100 == 0:
            print(f"  Generated: {i}/{count}")
    
    # Create summary file
    summary = {
        "batch_info": {
            "tier": tier,
            "count": count,
            "generated_at": datetime.now().isoformat(),
            "directory": directory
        },
        "licenses": [
            {
                "index": i + 1,
                "key": key,
                "file": os.path.basename(path)
            }
            for i, (key, path, _) in enumerate(results)
        ]
    }
    
    summary_file = os.path.join(directory, f"BATCH_{tier}_{count}_SUMMARY.json")
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Create keys-only file (untuk easy distribution)
    keys_file = os.path.join(directory, f"BATCH_{tier}_{count}_KEYS.txt")
    with open(keys_file, 'w') as f:
        f.write(f"Sentinel-X {tier} License Keys - {count} total\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        for i, (key, _, _) in enumerate(results, 1):
            f.write(f"{i:04d}. {key}\n")
    
    return results, summary_file, keys_file


def main():
    parser = argparse.ArgumentParser(
        description="Generate Sentinel-X license keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single license
  python tools/generate_license.py --trial
  python tools/generate_license.py --tier PRO
  
  # Batch generation (1000 licenses)
  python tools/generate_license.py --tier PRO --batch 1000
  python tools/generate_license.py --tier TRIAL --batch 1000
        """
    )
    
    tier_group = parser.add_mutually_exclusive_group(required=True)
    tier_group.add_argument(
        "--trial",
        action="store_true",
        help="Generate TRIAL license(s)"
    )
    tier_group.add_argument(
        "--tier",
        choices=["TRIAL", "PRO", "ENTERPRISE"],
        help="License tier"
    )
    
    parser.add_argument(
        "--batch",
        type=int,
        default=1,
        help="Number of licenses to generate (default: 1)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="tools/generated_keys",
        help="Output directory (default: tools/generated_keys)"
    )
    
    args = parser.parse_args()
    
    tier = "TRIAL" if args.trial else args.tier
    batch_count = args.batch
    
    print("=" * 60)
    print(f"Sentinel-X License Generator")
    print(f"Tier: {tier}")
    print(f"Count: {batch_count}")
    print("=" * 60)
    
    try:
        if batch_count > 1:
            # Batch generation
            results, summary_file, keys_file = generate_batch_licenses(
                tier=tier,
                count=batch_count,
                directory=args.output
            )
            
            print(f"\n✓ Batch generation complete!")
            print(f"  Total: {len(results)} licenses")
            print(f"  Summary: {summary_file}")
            print(f"  Keys file: {keys_file}")
            print(f"\nFiles saved to: {args.output}")
            
            # Show sample keys
            print(f"\nSample keys:")
            for i, (key, _, _) in enumerate(results[:5], 1):
                print(f"  {i:04d}. {key}")
            if len(results) > 5:
                print(f"  ... and {len(results) - 5} more")
                
        else:
            # Single license
            license_key, file_path, metadata = generate_single_license(
                tier=tier,
                directory=args.output
            )
            
            tier_name = metadata["tier"]
            expires_text = metadata["expires_at"]
            max_trades = metadata["max_trades"]
            features = ", ".join(metadata["features"])
            
            print(f"\n✓ {tier_name} license generated:")
            print(f"  Key:      {license_key}")
            print(f"  Expires:  {expires_text}")
            print(f"  Trades:   {max_trades if max_trades > 0 else 'Unlimited'}")
            print(f"  Features: {features}")
            print(f"\n  File: {file_path}")
        
        print("\n" + "=" * 60)
        print("IMPORTANT NOTES:")
        print("=" * 60)
        print("• PRO/ENTERPRISE licenses are LIFETIME (no expiry)")
        print("• Licenses are hardware-bound to first device")
        print("• Cannot transfer between devices")
        print("• TRIAL expires after 7 days (50 trade limit)")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Error generating license: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
