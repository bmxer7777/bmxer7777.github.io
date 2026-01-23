#!/usr/bin/env python3
"""
LYRIQ Tracker Daemon
Runs the location extractor every 5 minutes to keep location_history.json updated.
Forces Find My to refresh in the background.

Usage:
    python3 tracker_daemon.py

To run in background:
    nohup python3 tracker_daemon.py > daemon.log 2>&1 &

To stop:
    pkill -f tracker_daemon.py
"""

import subprocess
import time
import sys
from datetime import datetime
from pathlib import Path

# Configuration
POLL_INTERVAL = 300  # 5 minutes in seconds
SCRIPT_DIR = Path(__file__).parent
EXTRACTOR_SCRIPT = SCRIPT_DIR / "extract_location.py"


def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()


def run_extractor():
    """Run the location extractor script."""
    try:
        result = subprocess.run(
            [sys.executable, str(EXTRACTOR_SCRIPT)],
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if "New location recorded" in result.stdout:
            log("✓ New location recorded!")
            for line in result.stdout.split('\n'):
                if any(x in line for x in ['Lat:', 'Lon:', 'Last seen:', 'Location:']):
                    log(f"  {line.strip()}")
        elif "Location unchanged" in result.stdout:
            log("○ No new location")
        else:
            log("? Extractor output:")
            for line in result.stdout.split('\n')[-5:]:
                if line.strip():
                    log(f"  {line}")
        
        if result.stderr:
            log(f"⚠ Warnings: {result.stderr[:200]}")
            
    except subprocess.TimeoutExpired:
        log("⚠ Extractor timed out")
    except Exception as e:
        log(f"⚠ Error running extractor: {e}")


def refresh_findmy_cache():
    """
    Force Find My to refresh by opening it in the background,
    waiting for sync, then hiding it - all without stealing focus.
    """
    try:
        # Method 1: Use open -g (background) and then kill
        # This triggers iCloud sync without bringing window to front
        subprocess.run([
            "open", "-g", "-a", "FindMy"
        ], capture_output=True, timeout=5)
        
        log("  Triggered Find My sync...")
        time.sleep(5)  # Give it time to sync
        
        # Hide Find My window using AppleScript (keeps it running but invisible)
        subprocess.run([
            "osascript", "-e",
            'tell application "System Events" to set visible of process "FindMy" to false'
        ], capture_output=True, timeout=5)
        
    except Exception as e:
        log(f"  Find My refresh failed: {e}")
        # Try alternative method - just touch the cache to trigger refresh
        try:
            cache_path = Path.home() / "Library/Caches/com.apple.findmy.fmipcore"
            if cache_path.exists():
                # Reading the directory can sometimes trigger a sync
                list(cache_path.iterdir())
        except:
            pass


def main():
    log("=" * 50)
    log("LYRIQ Tracker Daemon Starting")
    log(f"Poll interval: {POLL_INTERVAL} seconds ({POLL_INTERVAL // 60} minutes)")
    log(f"Extractor: {EXTRACTOR_SCRIPT}")
    log("=" * 50)
    log("")
    log("Press Ctrl+C to stop")
    log("")
    
    # Run immediately on start
    log("Running initial check...")
    refresh_findmy_cache()
    time.sleep(3)
    run_extractor()
    
    # Then loop forever
    while True:
        log(f"\n--- Sleeping {POLL_INTERVAL // 60} minutes until next check ---")
        time.sleep(POLL_INTERVAL)
        
        log("\nRefreshing Find My...")
        refresh_findmy_cache()
        time.sleep(5)
        
        log("Extracting location...")
        run_extractor()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n\nDaemon stopped by user")
        sys.exit(0)
