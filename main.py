import argparse
import os
from pathlib import Path
from dotenv import load_dotenv
from productivity_tracker import ProductivityTracker

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Productivity Tracker")
    
    parser.add_argument(
        "--api-key",
        help="Google API key (can also be set via GOOGLE_API_KEY in .env)",
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration to run in minutes (default: 60)",
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="output",
        help="Output directory (default: ./output)",
    )

    args = parser.parse_args()
    
    # Get API key from args or environment
    api_key = args.api_key or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        parser.error("API key must be provided via --api-key or GOOGLE_API_KEY in .env file")
    
    output_dir = args.output
    
    # Create and run tracker
    tracker = ProductivityTracker(
        api_key=api_key,
        run_duration_minutes=args.duration,
        output_dir=output_dir,
    )
    
    tracker.run()

if __name__ == "__main__":
    main()