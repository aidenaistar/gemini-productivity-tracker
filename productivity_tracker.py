import os
import time
from datetime import datetime, timedelta
import json
from pathlib import Path
import threading
import logging
import sys
from PIL import ImageGrab, Image
import google.generativeai as genai
#from dotenv import load_dotenv

# Load environment variables from .env file
#load_dotenv()

# Load prompts from ./prompts/
batch_prompt = Path("prompts/batch.txt").read_text()
day_prompt = Path("prompts/day.txt").read_text()

class ProcessingTracker:
    def __init__(self, base_dir):
        self.tracking_file = Path(base_dir) / "processed_batches.json"
        self.load_tracking_data()

    def load_tracking_data(self):
        if self.tracking_file.exists():
            with open(self.tracking_file, 'r') as f:
                self.processed_batches = json.load(f)
        else:
            self.processed_batches = []

    def save_tracking_data(self):
        with open(self.tracking_file, 'w') as f:
            json.dump(self.processed_batches, f)

    def mark_as_processed(self, folder_path):
        self.processed_batches.append(str(folder_path))
        self.save_tracking_data()

    def is_processed(self, folder_path):
        return str(folder_path) in self.processed_batches

class ProductivityTracker:
    def __init__(self, api_key, run_duration_minutes=60, output_dir="output"):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        self.run_duration_minutes = run_duration_minutes
        self.output_dir = Path(output_dir) / datetime.now().strftime("%Y%m%d")
        Path(output_dir).mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        self.processing_tracker = ProcessingTracker(self.output_dir)
        self.current_batch_folder = None
        self.next_batch_time = None
        self.is_running = True
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('productivity_tracker.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def take_screenshot(self):
        """Capture a screenshot using PIL ImageGrab"""
        try:
            screenshot = ImageGrab.grab()
            return screenshot
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            return None

    def create_batch_folder(self, timestamp):
        """Create a new folder for the current batch"""
        folder_path = self.output_dir / timestamp
        folder_path.mkdir(exist_ok=True)
        return folder_path

    def analyze_batch(self, folder_path):
        """Analyze a batch of screenshots from a folder"""
        try:
            screenshots = []
            screenshot_files = sorted(folder_path.glob("screenshot_*.png"))
            
            for screenshot_path in screenshot_files:
                screenshot = Image.open(screenshot_path)
                screenshots.append(screenshot)

            if not screenshots:
                self.logger.warning(f"No screenshots found in {folder_path}")
                return None

            prompt = batch_prompt
            response = self.model.generate_content([prompt, *screenshots])
            
            if response:
                summary = response.text
                with open(folder_path / "summary.txt", "w", encoding='utf-8') as f:
                    f.write(summary)
                return summary
                
        except Exception as e:
            self.logger.error(f"Error analyzing batch: {e}")
            self.logger.error(f"Full error: {str(e)}")
            return None

    def screenshot_worker(self):
        """Worker thread for taking and saving screenshots"""
        # Initialize the first batch time to the next minute boundary
        current_time = datetime.now()
        self.next_batch_time = current_time + timedelta(minutes=1)
        self.next_batch_time = self.next_batch_time.replace(second=0, microsecond=0)
        
        # Create initial batch folder
        self.current_batch_folder = self.create_batch_folder(
            current_time.strftime("%H%M%S")
        )
        
        while self.is_running:
            current_time = datetime.now()
            
            # Check if it's time for a new batch
            if current_time >= self.next_batch_time:
                # Create new batch folder
                timestamp = current_time.strftime("%H%M%S")
                self.current_batch_folder = self.create_batch_folder(timestamp)
                
                # Set next batch time
                self.next_batch_time += timedelta(minutes=1)
                self.logger.info(f"Starting new batch: {timestamp}")
            
            # Take and save screenshot
            screenshot = self.take_screenshot()
            if screenshot:
                timestamp = current_time.strftime("%H%M%S")
                screenshot_path = self.current_batch_folder / f"screenshot_{timestamp}.png"
                screenshot.save(screenshot_path)
            
            # Calculate sleep time to maintain precise timing
            sleep_time = 1.0 - (time.time() % 1.0)
            time.sleep(sleep_time)

    def batch_processor(self):
        """Process unanalyzed batches"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Find unprocessed batch folders
                for folder in sorted(self.output_dir.iterdir()):
                    if (folder.is_dir() and 
                        not self.processing_tracker.is_processed(folder) and
                        folder != self.current_batch_folder):
                        
                        # Only process folders that are at least 1 minute old
                        folder_time = datetime.strptime(folder.name, "%H%M%S")
                        if (current_time - folder_time).total_seconds() >= 60:
                            self.logger.info(f"Processing batch folder: {folder}")
                            self.analyze_batch(folder)
                            self.processing_tracker.mark_as_processed(folder)
                
                time.sleep(5)  # Check for new batches every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Error in batch processor: {e}")
                time.sleep(5)

    def summarize_day(self):
        """Create a summary from all minute summaries"""
        try:
            all_summaries = []
            for folder in sorted(self.output_dir.iterdir()):
                if folder.is_dir():
                    summary_file = folder / "summary.txt"
                    if summary_file.exists():
                        with open(summary_file, "r", encoding='utf-8') as f:
                            all_summaries.append(f"Summary for {folder.name}:\n{f.read()}")

            if not all_summaries:
                self.logger.warning("No summaries found to analyze")
                return

            prompt = day_prompt + "\n".join(all_summaries)
            response = self.model.generate_content(prompt)
            
            if response:
                summary = response.text
                with open(self.output_dir / f"session_summary_{datetime.now().strftime('%H%M%S')}.txt", "w", encoding='utf-8') as f:
                    f.write(summary)
                
            self.logger.info("Day summary created")
            
        except Exception as e:
            self.logger.error(f"Error creating summary: {e}")
            self.logger.error(f"Full error: {str(e)}")


    def process_final_batch(self):
        if self.current_batch_folder and not self.processing_tracker.is_processed(self.current_batch_folder):
            self.logger.info(f"Processing final incomplete batch: {self.current_batch_folder}")
            self.analyze_batch(self.current_batch_folder)
            self.processing_tracker.mark_as_processed(self.current_batch_folder)
        
    
    def run(self):
        """Main run method"""
        try:
            self.logger.info("Starting productivity tracker...")
            self.logger.info(f"Will run for {self.run_duration_minutes} minutes")
            
            # Start worker threads
            screenshot_thread = threading.Thread(target=self.screenshot_worker)
            batch_thread = threading.Thread(target=self.batch_processor)
            
            screenshot_thread.start()
            batch_thread.start()
            
            # Run for specified duration
            start_time = datetime.now()
            duration_in_seconds = self.run_duration_minutes * 60
            while (datetime.now() - start_time).total_seconds() < duration_in_seconds:
                time.sleep(1)
                
            self.is_running = False
            
            # Wait for threads to complete
            screenshot_thread.join()
            batch_thread.join()
            
            # Process final incomplete batch if exists
            self.process_final_batch()
            
            # Create final summary
            self.summarize_day()
            
        except KeyboardInterrupt:
            self.logger.info("Stopping productivity tracker...")
            self.is_running = False
            # Process final incomplete batch if exists
            self.process_final_batch()
            self.summarize_day()
        except Exception as e:
            self.logger.error(f"Error in main run loop: {e}")
        finally:
            self.logger.info("Productivity tracker stopped")

if __name__ == "__main__":
    # Get API key from environment variable or command line argument
    api_key = os.getenv("GOOGLE_API_KEY") or sys.argv[1]
    
    # Create and run tracker
    tracker = ProductivityTracker(
        api_key=api_key,
        run_duration_minutes=2,  # Change this value as needed
        output_dir="output"
    )
    tracker.run()