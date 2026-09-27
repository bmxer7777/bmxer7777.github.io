#!/usr/bin/env python3
"""
LYRIQ AirTag Location Extractor
Reads Find My cache on macOS and logs AirTag locations to JSON.
Handles NSKeyedArchiver format used by modern macOS.
"""

import json
import os
import subprocess
import re
from datetime import datetime
from pathlib import Path

# Find My cache locations (varies by macOS version)
CACHE_LOCATIONS = [
    Path.home() / "Library/Caches/com.apple.findmy.fmipcore/Items.data",
    Path.home() / "Library/Caches/com.apple.findmy.fmipcore/Devices.data",
]

# Output file for location history
OUTPUT_FILE = Path(__file__).parent / "location_history.json"

# Set this to your AirTag's name (as shown in Find My app)
AIRTAG_NAME = "ERAUBCU LYRIQ"  # Updated to match your AirTag


def find_cache_file():
    """Find the first available cache file."""
    for path in CACHE_LOCATIONS:
        if path.exists():
            return path
    return None


def load_findmy_items_via_plutil(cache_path):
    """Use plutil to convert NSKeyedArchiver format to readable output."""
    try:
        # Try converting to JSON first
        result = subprocess.run(
            ["plutil", "-convert", "json", "-o", "-", str(cache_path)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return json.loads(result.stdout), "json"
    except:
        pass
    
    # Fall back to printing raw format
    try:
        result = subprocess.run(
            ["plutil", "-p", str(cache_path)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout, "raw"
    except:
        pass
    
    return None, None


def parse_raw_plutil_output(raw_output, airtag_name):
    """Parse the raw plutil -p output to extract location data."""
    # This is a bit hacky but works for extracting data from NSKeyedArchiver output
    lines = raw_output.split('\n')
    
    current_item = {}
    items = []
    in_item = False
    brace_depth = 0
    
    # Look for patterns in the output
    name_pattern = re.compile(r'"name"\s*=>\s*"([^"]+)"')
    lat_pattern = re.compile(r'"latitude"\s*=>\s*([-\d.]+)')
    lon_pattern = re.compile(r'"longitude"\s*=>\s*([-\d.]+)')
    accuracy_pattern = re.compile(r'"horizontalAccuracy"\s*=>\s*([-\d.]+)')
    timestamp_pattern = re.compile(r'"timeStamp"\s*=>\s*([-\d.]+)')
    
    current_name = None
    current_lat = None
    current_lon = None
    current_acc = None
    current_ts = None
    
    for line in lines:
        # Check for name
        name_match = name_pattern.search(line)
        if name_match:
            # Save previous item if exists
            if current_name and current_lat is not None:
                items.append({
                    "name": current_name,
                    "latitude": current_lat,
                    "longitude": current_lon,
                    "accuracy": current_acc,
                    "timestamp": current_ts
                })
            current_name = name_match.group(1)
            current_lat = None
            current_lon = None
        
        lat_match = lat_pattern.search(line)
        if lat_match:
            current_lat = float(lat_match.group(1))
            
        lon_match = lon_pattern.search(line)
        if lon_match:
            current_lon = float(lon_match.group(1))
            
        acc_match = accuracy_pattern.search(line)
        if acc_match:
            current_acc = float(acc_match.group(1))
            
        ts_match = timestamp_pattern.search(line)
        if ts_match:
            current_ts = float(ts_match.group(1))
    
    # Don't forget the last item
    if current_name and current_lat is not None:
        items.append({
            "name": current_name,
            "latitude": current_lat,
            "longitude": current_lon,
            "accuracy": current_acc,
            "timestamp": current_ts
        })
    
    return items


def find_airtag(items, name):
    """Find a specific AirTag by name."""
    name_lower = name.lower()
    
    # Exact match first
    for item in items:
        item_name = item.get("name", "")
        if item_name.lower() == name_lower:
            return item
    
    # Partial match
    for item in items:
        item_name = item.get("name", "")
        if name_lower in item_name.lower() or item_name.lower() in name_lower:
            return item
    
    return None


def load_history():
    """Load existing location history."""
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r") as f:
            return json.load(f)
    return {"airtag_name": AIRTAG_NAME, "locations": []}


def save_history(history):
    """Save location history to JSON."""
    with open(OUTPUT_FILE, "w") as f:
        json.dump(history, f, indent=2)


def main():
    print(f"Looking for AirTag: {AIRTAG_NAME}")
    print(f"=" * 50)
    
    # Find cache file
    cache_path = find_cache_file()
    if not cache_path:
        print("\nError: Find My cache not found!")
        print("Checked locations:")
        for loc in CACHE_LOCATIONS:
            print(f"  - {loc}")
        print("\nMake sure you're signed into iCloud with Find My enabled.")
        print("Try opening the Find My app to refresh the cache.")
        return
    
    print(f"Found cache: {cache_path}")
    
    # Load data using plutil
    data, format_type = load_findmy_items_via_plutil(cache_path)
    
    if data is None:
        print("\nError: Could not read Find My cache.")
        print("Try running: plutil -p '{}'".format(cache_path))
        return
    
    print(f"Cache format: {format_type}")
    
    # Parse based on format
    if format_type == "json":
        # Direct JSON array from plutil
        if isinstance(data, list):
            # Items are directly in the array, location is nested
            items = []
            for item in data:
                parsed = {
                    "name": item.get("name", "Unknown"),
                    "raw": item  # Keep raw data for location extraction
                }
                # Extract location if present
                loc = item.get("location")
                if loc and isinstance(loc, dict):
                    parsed["latitude"] = loc.get("latitude")
                    parsed["longitude"] = loc.get("longitude")
                    parsed["accuracy"] = loc.get("horizontalAccuracy")
                    parsed["timestamp"] = loc.get("timeStamp")
                    parsed["address"] = item.get("address", {})
                items.append(parsed)
        elif isinstance(data, dict):
            items = data.get("$objects", [])
        else:
            items = []
    else:
        # Raw plutil output - need to parse
        print("\nParsing raw cache data...")
        items = parse_raw_plutil_output(data, AIRTAG_NAME)
    
    if not items:
        print("\nNo items found in cache. Raw output preview:")
        if isinstance(data, str):
            print(data[:2000])
        else:
            print(json.dumps(data, indent=2, default=str)[:2000])
        return
    
    # Debug: dump full structure for first item with our name
    print("\n[DEBUG] Looking for location structure...")
    if isinstance(data, dict):
        # Save full JSON for inspection
        debug_file = Path(__file__).parent / "debug_cache.json"
        with open(debug_file, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"[DEBUG] Full cache saved to: {debug_file}")
    
    # List all items
    print(f"\nFound {len(items)} items in Find My:")
    for item in items:
        name = item.get("name", "Unknown")
        lat = item.get("latitude", "?")
        lon = item.get("longitude", "?")
        print(f"  - {name}: ({lat}, {lon})")
    
    # Find our AirTag
    airtag = find_airtag(items, AIRTAG_NAME)
    if not airtag:
        print(f"\nError: Could not find AirTag named '{AIRTAG_NAME}'")
        print("Update AIRTAG_NAME in this script to match one of the names above.")
        return
    
    # Extract location
    lat = airtag.get("latitude")
    lon = airtag.get("longitude")
    
    if lat is None or lon is None:
        print(f"\nNo location data available for {AIRTAG_NAME}")
        return
    
    location = {
        "latitude": lat,
        "longitude": lon,
        "accuracy": airtag.get("accuracy"),
        "timestamp": airtag.get("timestamp", 0),
        "address": airtag.get("address", {})
    }
    
    # Handle timestamp (might be in milliseconds or seconds)
    if location["timestamp"] and location["timestamp"] > 1e12:
        location["timestamp"] = location["timestamp"] / 1000
    
    # Load history and check for duplicates
    history = load_history()
    
    is_new = True
    if history["locations"]:
        last = history["locations"][-1]
        if (last.get("latitude") == location["latitude"] and 
            last.get("longitude") == location["longitude"]):
            is_new = False
    
    if is_new:
        location["recorded_at"] = datetime.now().isoformat()
        history["locations"].append(location)
        save_history(history)
        print(f"\n✓ New location recorded!")
    else:
        print(f"\n○ Location unchanged since last check")
    
    # Print current location
    print(f"\nCurrent location:")
    print(f"  Lat: {location['latitude']}")
    print(f"  Lon: {location['longitude']}")
    if location.get("accuracy"):
        print(f"  Accuracy: {location['accuracy']}m")
    
    # Print address if available
    addr = location.get("address", {})
    if addr:
        city = addr.get("locality", "")
        state = addr.get("administrativeArea", "")
        if city or state:
            print(f"  Location: {city}, {state}".strip(", "))
    
    if location.get("timestamp"):
        try:
            ts = datetime.fromtimestamp(location["timestamp"])
            print(f"  Last seen: {ts.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            pass
    
    print(f"\nTotal locations recorded: {len(history['locations'])}")
    print(f"History saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
