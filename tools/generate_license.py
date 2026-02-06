#!/usr/bin/env python3
"""
License Key Generator for Sentinel-X

Generates license keys for different tiers:
- TRIAL: 7 days, 50 trades
- PRO: Lifetime (no expiry), unlimited trades
- ENTERPRISE: Lifetime + white label + support

Usage:
    python tools/generate_license.py --trial
    python tools/generate_license.py --tier PRO --customer "John Doe"
    python tools/generate_license.py --tier ENTERPRISE --customer "Acme Corp"
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


def generate_license(tier: str, customer: str = "Unknown", directory: str = "tools/generated_keys"):
    """
    Generate a license key and save metadata.
    
    Args:
        tier: License tier (TRIAL, PRO, ENTERPRISE)
        customer: Customer name for tracking
        directory: Directory to save license info
        
    Returns:
        (license_key, file_path, metadata)
    """
    lm = LicenseManager()
    
    license_key = lm.generate_license_key(tier)
    license_data = lm.create_license_data(license_key, tier)
    
    os.makedirs(directory, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(directory, f"{customer}_{tier}_{timestamp}.json")
    
    metadata = {
        "license_key": license_key,
        "tier": tier,
        "customer": customer,
        "generated_at": datetime.now().isoformat(),
        "hardware_id": lm.hardware_id,
        "expires_at": "Lifetime" if tier in ["PRO", "ENTERPRISE"] else "7 days from activation",
        "max_trades": 50 if tier == "TRIAL" else 0,
        "features": license_data["features"]
    }
    
    with open(file_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    key_only_file = os.path.join(directory, f"{customer}_{tier}_KEY.txt")
    with open(key_only_file, 'w') as f:
        f.write(license_key)
    
    return license_key, file_path, metadata


def main():
    parser = argparse.ArgumentParser(
        description="Generate Sentinel-X license keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/generate_license.py --trial
  python tools/generate_license.py --tier PRO --customer "John Doe"
  python tools/generate_license.py --tier ENTERPRISE --customer "Acme Corp"
        """
    )
    
    tier_group = parser.add_mutually_exclusive_group(required=True)
    tier_group.add_argument(
        "--trial",
        action="store_true",
        help="Generate and print TRIAL license"
    )
    tier_group.add_argument(
        "--tier",
        choices=["PRO", "ENTERPRISE"],
        help="License tier (PRO/ENTERPRISE)"
    )
    
    parser.add_argument(
        "--customer",
        type=str,
        default="Unknown",
        help="Customer name for tracking"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="tools/generated_keys",
        help="Output directory"
    )
    
    args = parser.parse_args()
    
    tier = "TRIAL" if args.trial else args.tier
    print("=" * 60)
    print(f"Generating {tier} license for {args.customer}")
    print("=" * 60)
    print()
    
    try:
        license_key, file_path, metadata = generate_license(
            tier=tier,
            customer=args.customer,
            directory=args.output
        )
        
        # Print license info
        tier_name = metadata["tier"]
        expires_text = metadata["expires_at"]
        max_trades = metadata["max_trades"]
        features = ", ".join(metadata["features"])
        
        print(f" {tier_name} license generated:")
        print(f"   Key:      {license_key}")
        print(f"   Expires:  {expires_text}")
        print(f"   Trades:   {max_trades if max_trades > 0 else 'Unlimited'}")
        print(f"   Features: {features}")
        print()
        
        print("=" * 60)
        print("INSTRUCTIONS:")
        print("=" * 60)
        print("1. Copy the license key above")
        print("2. Open Sentinel-X GUI")
        print("3. Paste in License tab > Activate")
        print("4. Restart application")
        print()
        print("[ATTENTION]  Important:")
        print("   - License locked to first device")
        print("   - Cannot transfer to other device")
        print("   - Lifetime validity (PRO/ENTERPRISE)")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Error generating license: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()