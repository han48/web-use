#!/usr/bin/env python3
"""
Utility script for managing replay operations.

Commands:
    convert     - Convert old record format to enhanced format
    replay      - Replay a record using Selenium
    inspect     - Inspect record contents
    list        - List all available records
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure repo root is on sys.path so `src` imports work when running this script directly.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Setup logging
LOGS_DIR = Path('logs')
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE_PATH = LOGS_DIR / f"replay_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
file_handler = logging.FileHandler(LOG_FILE_PATH, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout), file_handler]
)
logger = logging.getLogger(__name__)


def list_records(records_dir: Path = None) -> list[Path]:
    """List all available record files."""
    if records_dir is None:
        records_dir = Path("records")
    
    if not records_dir.exists():
        logger.warning(f"Records directory not found: {records_dir}")
        return []
    
    records = sorted(records_dir.glob("web-use-record_*.json"))
    
    print(f"\n📁 Found {len(records)} record(s) in {records_dir}:\n")
    for i, record in enumerate(records, 1):
        size = record.stat().st_size / 1024  # KB
        print(f"  {i}. {record.name} ({size:.1f} KB)")
    print()
    
    return records


def inspect_record(record_path: Path):
    """Inspect and display record contents."""
    try:
        with open(record_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check format version
        if isinstance(data, list):
            # Old format (array of events)
            print(f"\n📋 Record Format: Old (v1.0)")
            print(f"   Total events: {len(data)}")
            
            # Count event types
            event_counts = {}
            tool_calls = []
            
            for event in data:
                event_type = event.get("type", "unknown")
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
                
                if event_type == "TOOL_CALL":
                    tool_name = event.get("data", {}).get("tool_name", "unknown")
                    tool_calls.append(tool_name)
            
            print(f"\n   Event breakdown:")
            for event_type, count in sorted(event_counts.items()):
                print(f"     - {event_type}: {count}")
            
            print(f"\n   Tools used:")
            from collections import Counter
            for tool, count in sorted(Counter(tool_calls).items()):
                print(f"     - {tool}: {count}x")
        
        elif isinstance(data, dict):
            # New enhanced format
            version = data.get("version", "unknown")
            print(f"\n📋 Record Format: Enhanced (v{version})")
            records = data.get("records", [])
            print(f"   Total actions: {len(records)}")
            
            if records:
                print(f"\n   Actions:")
                for i, record in enumerate(records[:10], 1):  # Show first 10
                    action = record.get("action_type", "unknown")
                    tool = record.get("tool_name", "unknown")
                    success = "✅" if record.get("success") else "❌"
                    print(f"     {i}. [{success}] {action} ({tool})")
                
                if len(records) > 10:
                    print(f"     ... and {len(records) - 10} more")
                
                print(f"\n   Metadata:")
                print(f"     - Recorded at: {data.get('recorded_at', 'N/A')}")
                if records[0].get("page_url"):
                    print(f"     - Pages visited: {len(set(r.get('page_url') for r in records))}")
        
        print()
    except Exception as e:
        logger.error(f"Failed to inspect record: {e}")
        sys.exit(1)


def convert_record(old_path: Path, new_path: Optional[Path] = None):
    """Convert old record format to enhanced format."""
    try:
        if new_path is None:
            new_path = old_path.parent / f"{old_path.stem}_enhanced.json"
        
        from src.agent.replay import convert_to_enhanced_format
        
        logger.info(f"Converting: {old_path}")
        convert_to_enhanced_format(old_path, new_path)
        logger.info(f"✅ Saved enhanced record to: {new_path}")
        print(f"\n✨ Conversion complete!")
        print(f"   Input:  {old_path}")
        print(f"   Output: {new_path}\n")
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        sys.exit(1)


def replay_record(record_path: Path, browser: str = "chrome", headless: bool = False, verbose: bool = True):
    """Replay a record using Selenium."""
    try:
        from src.agent.replay import SeleniumReplayer, ReplayConfig
        
        screenshots_dir = record_path.parent / "replay_screenshots"
        
        config = ReplayConfig(
            browser=browser,
            headless=headless,
            screenshots_dir=screenshots_dir,
            verbose=verbose,
            retry_count=3,
        )
        
        print(f"\n🎬 Starting replay...")
        print(f"   Record: {record_path}")
        print(f"   Browser: {browser} {'(headless)' if headless else ''}")
        print(f"   Screenshots: {screenshots_dir}")
        print(f"   Log file: {LOG_FILE_PATH}\n")
        
        replayer = SeleniumReplayer(config)
        results = replayer.replay_from_file(record_path)
        replayer.close()
        
        # Log replay summary and failed actions to the file log too
        logger.info(
            "Replay summary: total=%d, successful=%d, failed=%d, skipped=%d",
            results.get('total_events', 0),
            results.get('successful', 0),
            results.get('failed', 0),
            results.get('skipped', 0),
        )
        
        if results.get('failed', 0) > 0:
            for detail in results.get('details', []):
                if not detail.get('result', {}).get('success'):
                    event = detail.get('event', {})
                    data = event.get('data', {})
                    logger.error(
                        "Replay failed action: %s -> %s",
                        data.get('tool_name'),
                        detail.get('result', {}).get('error'),
                    )

        # Print results
        print(f"\n📊 Replay Results:")
        print(f"   Total events: {results.get('total_events', 0)}")
        print(f"   Successful: {results.get('successful', 0)} ✅")
        print(f"   Failed: {results.get('failed', 0)} ❌")
        print(f"   Skipped: {results.get('skipped', 0)} ⏭️")
        
        if results.get('failed', 0) > 0:
            print(f"\n   Failed actions:")
            for detail in results.get('details', []):
                if not detail.get('result', {}).get('success'):
                    event = detail.get('event', {})
                    data = event.get('data', {})
                    print(f"     - {data.get('tool_name')}: {detail.get('result', {}).get('error')}")
        
        print()
    except Exception as e:
        logger.error(f"Replay failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Web-use replay management utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all records
  %(prog)s list

  # Inspect a record
  %(prog)s inspect records/web-use-record_*.json

  # Convert old format to enhanced
  %(prog)s convert records/old-record.json

  # Replay a record
  %(prog)s replay records/web-use-record_*.json --browser chrome

  # Replay with custom options
  %(prog)s replay records/session.json --browser firefox --headless false
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List command
    subparsers.add_parser("list", help="List all available records")
    
    # Inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect record contents")
    inspect_parser.add_argument("record", type=Path, help="Record file path")
    
    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert old record format to enhanced")
    convert_parser.add_argument("record", type=Path, help="Record file to convert")
    convert_parser.add_argument("--output", "-o", type=Path, help="Output path (auto-generated if not specified)")
    
    # Replay command
    replay_parser = subparsers.add_parser("replay", help="Replay a record using Selenium")
    replay_parser.add_argument("record", type=Path, help="Record file to replay")
    replay_parser.add_argument("--browser", "-b", default="chrome", choices=["chrome", "firefox", "edge"],
                             help="Browser to use (default: chrome)")
    replay_parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    replay_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_records()
    
    elif args.command == "inspect":
        inspect_record(args.record)
    
    elif args.command == "convert":
        convert_record(args.record, args.output)
    
    elif args.command == "replay":
        replay_record(args.record, args.browser, args.headless, args.verbose)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
