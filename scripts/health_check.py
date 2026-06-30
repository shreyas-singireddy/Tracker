#!/usr/bin/env python3
"""FitOS System Diagnostics & Health Check Utility.

Runs database checks, service lookups, module audits, and dependency verification.
Returns status: GREEN, YELLOW, or RED.
Exits with 0 on GREEN/YELLOW, and 1 on RED.
"""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.core.bootloader import Bootloader
from app.registry.module_registry import module_registry, ServiceRegistry

def run_health_check():
    print("=" * 60)
    print("           FitOS System Health Diagnostics")
    print("=" * 60)
    
    # 1. Boot system to register modules and services
    print("[1/4] Booting FitOS System Registry...")
    try:
        Bootloader.boot()
        print("  [PASS] Boot sequence passed.")
    except Exception as e:
        print(f"  [FAIL] Critical Boot Failure: {e}")
        print("\nSTATUS: RED (System failed to boot)")
        sys.exit(1)

    # 2. Module Health Checks
    print("\n[2/4] Auditing Domain Modules...")
    all_green = True
    any_yellow = False
    
    modules_health = module_registry.health_check_all()
    for mod_name, check_res in modules_health["modules"].items():
        status = check_res.get("status", "RED")
        details = check_res.get("details", "")
        if status == "GREEN":
            print(f"  [PASS] {mod_name.upper():<10} : GREEN - {details}")
        elif status == "YELLOW":
            print(f"  [WARN] {mod_name.upper():<10} : YELLOW - {details}")
            any_yellow = True
        else:
            print(f"  [FAIL] {mod_name.upper():<10} : RED - {details}")
            all_green = False

    # 3. Service Lookup Verification
    print("\n[3/4] Testing Service Registry Lookup Readiness...")
    required_services = [
        "WorkoutService",
        "NutritionService",
        "HabitService",
        "RecoveryService",
        "AICoachService",
        "AnalyticsService"
    ]
    for s_name in required_services:
        try:
            service = ServiceRegistry.get(s_name)
            if service is not None:
                print(f"  [PASS] {s_name:<20} : READY")
            else:
                print(f"  [WARN] {s_name:<20} : EMPTY INSTANCE")
                any_yellow = True
        except KeyError:
            print(f"  [FAIL] {s_name:<20} : UNREGISTERED")
            all_green = False

    # 4. System Settings Check
    print("\n[4/4] Verifying Configuration Settings...")
    print(f"  * Environment    : {settings.ENV}")
    print(f"  * Version        : {settings.VERSION}")
    print(f"  * Offline First  : {settings.OFFLINE_MODE} (Required: True)")
    print(f"  * Database Path  : {settings.DB_PATH}")
    
    if not settings.OFFLINE_MODE:
        print("  [FAIL] OFFLINE_MODE setting must be Enforced!")
        all_green = False

    # Aggregate Status
    print("\n" + "=" * 60)
    if not all_green or modules_health["status"] == "RED":
        print("FINAL STATUS: RED (Critical Failure Detected)")
        print("=" * 60)
        sys.exit(1)
    elif any_yellow or modules_health["status"] == "YELLOW":
        print("FINAL STATUS: YELLOW (Warnings Present)")
        print("=" * 60)
        sys.exit(0)
    else:
        print("FINAL STATUS: GREEN (All Systems Healthy)")
        print("=" * 60)
        sys.exit(0)

if __name__ == "__main__":
    run_health_check()
