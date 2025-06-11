
import json
import os
import time
from datetime import datetime

class ProgressTracker:
    def __init__(self, progress_file="progress.json"):
        self.progress_file = progress_file
        self.reset_progress()
    
    def reset_progress(self):
        """Reset progress to 0%"""
        self.update_progress(0, "Initializing...")
    
    def update_progress(self, percentage, message="Processing..."):
        """Update progress percentage and message"""
        progress_data = {
            "percentage": min(100, max(0, percentage)),
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "completed": percentage >= 100
        }
        
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f)
        except Exception as e:
            print(f"Error updating progress: {e}")
    
    def get_progress(self):
        """Get current progress"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading progress: {e}")
        
        return {
            "percentage": 0,
            "message": "Ready to start",
            "timestamp": datetime.now().isoformat(),
            "completed": False
        }
    
    def complete(self, message="Processing completed successfully!"):
        """Mark progress as complete"""
        self.update_progress(100, message)

# Global progress tracker instance
progress_tracker = ProgressTracker()