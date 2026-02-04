# import time
# from .config import FETCH_INTERVAL_HOURS

# def run_forever(task):
#     while True:
#         task()
#         # time.sleep(FETCH_INTERVAL_HOURS * 3600)
#         time.sleep(10)  # For testing purposes, sleep for 10 seconds instead of hours


import time
from datetime import datetime
# from .config import FETCH_INTERVAL_HOURS
import os
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Load fetch interval from config or use default
FETCH_INTERVAL_HOURS = int(os.getenv("FETCH_INTERVAL_HOURS"))

def run_forever(task):
    """
    Run the task continuously at the specified interval.
    
    Args:
        task: Function to execute on each cycle
    """
    interval_seconds = FETCH_INTERVAL_HOURS * 3600
    
    print(f"[Scheduler] Starting continuous operation")
    print(f"[Scheduler] Interval: {FETCH_INTERVAL_HOURS} hours ({interval_seconds} seconds)")
    
    cycle_count = 0
    
    while True:
        cycle_count += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"\n{'='*60}")
        print(f"[Scheduler] Cycle #{cycle_count} - {timestamp}")
        print(f"{'='*60}")
        
        try:
            task()
            print(f"[Scheduler] Cycle #{cycle_count} completed successfully")
        except KeyboardInterrupt:
            print("\n[Scheduler] Interrupted by user. Shutting down...")
            break
        except Exception as e:
            print(f"[Scheduler] ERROR in cycle #{cycle_count}: {e}")
            print(f"[Scheduler] Continuing to next cycle...")
        
        print(f"[Scheduler] Sleeping for {FETCH_INTERVAL_HOURS} hours...")
        print(f"[Scheduler] Next run at: {datetime.fromtimestamp(time.time() + interval_seconds).strftime('%Y-%m-%d %H:%M:%S')}")
        
        time.sleep(interval_seconds)
        # time.sleep(10)  # For testing purposes, sleep for 10 seconds instead of hours

# Alternative: Use this for testing with shorter intervals
def run_forever_testing(task, test_interval_seconds=10):
    """Testing version with shorter intervals"""
    print(f"[Scheduler] TESTING MODE - Running every {test_interval_seconds} seconds")
    
    cycle_count = 0
    while True:
        cycle_count += 1
        print(f"\n[Test Cycle #{cycle_count}] {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            task()
        except KeyboardInterrupt:
            print("\n[Scheduler] Stopped by user")
            break
        except Exception as e:
            print(f"[Scheduler] Error: {e}")
        
        time.sleep(test_interval_seconds)