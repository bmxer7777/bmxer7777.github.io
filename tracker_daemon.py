#!/usr/bin/env python3
"""
LYRIQ Tracker Daemon
Runs the location extractor every 5 minutes to keep location_history.json updated.
Forces Find My to refresh in the background.
Auto-pushes to GitHub when there's a new location.

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
POLL_INTERVAL = 60  # 5 minutes in seconds
SCRIPT_DIR = Path(__file__).parent
EXTRACTOR_SCRIPT = SCRIPT_DIR / "extract_location.py"
GITHUB_PUSH_ENABLED = True  # Set to False to disable auto-push


def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()


def push_to_github():
    """Commit and push location_history.json to GitHub."""
    if not GITHUB_PUSH_ENABLED:
        return
    
    # Check if this is a git repo
    if not (SCRIPT_DIR / ".git").exists():
        log("  ⚠ Not a git repo, skipping push")
        return
    
    try:
        # Add the JSON file
        subprocess.run(
            ["git", "add", "location_history.json"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            timeout=30
        )
        
        # Commit with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        result = subprocess.run(
            ["git", "commit", "-m", f"Location update {timestamp}"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if "nothing to commit" in result.stdout:
            log("  ○ No changes to push")
            return
        
        # Push to GitHub
        result = subprocess.run(
            ["git", "push"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            log("  ✓ Pushed to GitHub")
        else:
            log(f"  ⚠ Push failed: {result.stderr[:100]}")
            
    except subprocess.TimeoutExpired:
        log("  ⚠ Git operation timed out")
    except Exception as e:
        log(f"  ⚠ Git error: {e}")


def run_extractor():
    """Run the location extractor script. Returns True if new location recorded."""
    try:
        result = subprocess.run(
            [sys.executable, str(EXTRACTOR_SCRIPT)],
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        new_location = False
        
        if "New location recorded" in result.stdout:
            log("✓ New location recorded!")
            new_location = True
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
        
        return new_location
            
    except subprocess.TimeoutExpired:
        log("⚠ Extractor timed out")
        return False
    except Exception as e:
        log(f"⚠ Error running extractor: {e}")
        return False


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
    log(f"GitHub push: {'Enabled' if GITHUB_PUSH_ENABLED else 'Disabled'}")
    log("=" * 50)
    log("")
    log("Press Ctrl+C to stop")
    log("")
    
    # Run immediately on start
    log("Running initial check...")
    refresh_findmy_cache()
    time.sleep(3)
    new_location = run_extractor()
    if new_location:
        push_to_github()
    
    # Then loop forever
    while True:
        log(f"\n--- Sleeping {POLL_INTERVAL // 60} minutes until next check ---")
        time.sleep(POLL_INTERVAL)
        
        log("\nRefreshing Find My...")
        refresh_findmy_cache()
        time.sleep(5)
        
        log("Extracting location...")
        new_location = run_extractor()
        
        if new_location:
            push_to_github()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n\nDaemon stopped by user")
        sys.exit(0)
