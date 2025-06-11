"""
Batch Processing Module for Network Topology Visualization
Handles batch processing of multiple network equipment images
"""
import os
import time
import shutil
import logging
import subprocess
import pickle
from threading import Thread, Lock
from queue import Queue
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Config Paths --- (Will import from app.py when used)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEGMENT_OUTPUT_DIR = os.path.join(BASE_DIR, "static", "segmented_outputs")
BATCH_UPLOAD_DIR = os.path.join(BASE_DIR, "batch_uploads")
BATCH_RESULTS_DIR = os.path.join(BASE_DIR, "static", "batch_results")
CROPPED_OUTPUT = os.path.join(BASE_DIR, "cropped_clip_data.pkl")
CATALOG_PATH = os.path.join(BASE_DIR, "all_categories_data.pkl")
METADATA_PATH = os.path.join(BASE_DIR, "metadata.pkl")

# Ensure batch directories exist
os.makedirs(BATCH_UPLOAD_DIR, exist_ok=True)
os.makedirs(BATCH_RESULTS_DIR, exist_ok=True)

# Create processing queues
batch_queue = Queue()
processing_lock = Lock()
batch_status = {}

def clean_batch_directory(batch_id):
    """Clean the batch directory for a specific batch ID"""
    batch_dir = os.path.join(BATCH_RESULTS_DIR, batch_id)
    if os.path.exists(batch_dir):
        shutil.rmtree(batch_dir)
    os.makedirs(batch_dir, exist_ok=True)
    logger.debug(f"Cleaned batch directory: {batch_dir}")
    return batch_dir

def clean_segmented_outputs():
    """Clean the segmented outputs directory to remove old files"""
    # First, delete the entire directory if it exists
    if os.path.exists(SEGMENT_OUTPUT_DIR):
        shutil.rmtree(SEGMENT_OUTPUT_DIR)

    # Then recreate the empty directory and the category subdirectories
    os.makedirs(SEGMENT_OUTPUT_DIR, exist_ok=True)

    # Create subdirectories for each component type
    for category in ['Cable', 'Port', 'Rack', 'Switch']:
        os.makedirs(os.path.join(SEGMENT_OUTPUT_DIR, category), exist_ok=True)

    # Log the clean operation
    logger.debug(f"Cleaned segmented outputs directory: {SEGMENT_OUTPUT_DIR}")

def process_single_image(image_path, batch_id, image_index):
    """Process a single image in the batch"""
    try:
        # Update status
        batch_status[batch_id]['images'][image_index]['status'] = 'processing'
        batch_status[batch_id]['images'][image_index]['start_time'] = time.time()

        # Clean outputs
        clean_segmented_outputs()

        # 1. Run segmentation
        logger.debug(f"Running segmentation for image: {image_path}")
        result = subprocess.run(["python", "segment.py", image_path], 
                                capture_output=True, text=True, check=True)

        # 2. Generate cropped embeddings
        logger.debug("Generating cropped embeddings")
        result = subprocess.run(["python", "cropped_embeddings.py", 
                                SEGMENT_OUTPUT_DIR, CROPPED_OUTPUT],
                                capture_output=True, text=True, check=True)

        # 3. Create results directory for this image
        image_result_dir = os.path.join(BATCH_RESULTS_DIR, batch_id, f"image_{image_index}")
        os.makedirs(image_result_dir, exist_ok=True)

        # 4. Copy segmented outputs to results directory
        for category in ['Cable', 'Port', 'Rack', 'Switch']:
            category_src = os.path.join(SEGMENT_OUTPUT_DIR, category)
            category_dst = os.path.join(image_result_dir, category)
            os.makedirs(category_dst, exist_ok=True)

            # Copy all files in this category
            if os.path.exists(category_src):
                for filename in os.listdir(category_src):
                    src_file = os.path.join(category_src, filename)
                    dst_file = os.path.join(category_dst, filename)
                    if os.path.isfile(src_file):
                        shutil.copy2(src_file, dst_file)

        # 5. Copy coordinates data to results directory
        coordinates_src = os.path.join(SEGMENT_OUTPUT_DIR, "coordinates.json")
        coordinates_dst = os.path.join(image_result_dir, "coordinates.json")
        if os.path.exists(coordinates_src):
            shutil.copy2(coordinates_src, coordinates_dst)
            logger.debug(f"Copied coordinates data to: {coordinates_dst}")

        # 5. Create unique CSV and HTML outputs for this image
        image_csv = os.path.join(image_result_dir, "matched_results.csv")
        image_html = os.path.join(image_result_dir, "matched_results.html")

        # 6. Run comparison with unique outputs
        logger.debug(f"Running comparison for image {image_index}")
        result = subprocess.run([
            "python", "comparision.py",
            CATALOG_PATH,
            CROPPED_OUTPUT,
            METADATA_PATH,
            image_csv,
            image_html
        ], capture_output=True, text=True, check=True)

        # 7. Format the CSV and HTML to match the regular results format
        try:
            # Process the CSV file to match the regular results format
            if os.path.exists(image_csv):
                import pandas as pd

                # Read the CSV
                df = pd.read_csv(image_csv, keep_default_na=False)

                # Filter to only keep rows with similarity score > 0.7
                if 'similarity_score' in df.columns:
                    df = df[df['similarity_score'] > 0.7]

                # Function to fix path case sensitivity and backslashes for the filesystem
                def fix_path(path):
                    if isinstance(path, str) and "segmented_outputs" in path:
                        # Fix path separators - ensure forward slashes
                        path = path.replace('\\', '/')

                        # If path doesn't include the leading slash add it
                        if not path.startswith('/'):
                            path = '/' + path

                        # Fix case sensitivity in component type directories
                        for component in ['Cable', 'Rack', 'Switch', 'Port']:
                            path = path.replace(f'/segmented_outputs/{component}/', 
                                               f'/segmented_outputs/{component.lower()}/')

                    return path

                # Fix paths in the main data columns
                if 'cropped_image' in df.columns:
                    df['cropped_image'] = df['cropped_image'].apply(fix_path)

                # Function to create HTML image tag with fallback and click handler
                def img_html(path):
                    if not path or path == 'nan':
                        return ''

                    # Make sure path has the correct separator for web display
                    if isinstance(path, str):
                        path = path.replace('\\', '/')

                    return f'<img src="{path}" alt="Component" style="width: 100px; height: auto; border-radius: 4px; cursor: pointer;" onclick="showOriginalWithHighlight(\'{path}\')" onerror="this.onerror=null; this.src=\'/static/images/image-not-found.svg\'; this.alt=\'Image not found\'" title="Click to view original image with highlighted crop area" />'

                # Create modified DataFrame with only the required columns
                display_df = pd.DataFrame()

                # Capture category
                if 'category' in df.columns:
                    display_df['category'] = df['category']

                # Capture name
                if 'name' in df.columns:
                    display_df['name'] = df['name']

                # Capture description (ensure it's complete)
                if 'description' in df.columns:
                    display_df['description'] = df['description']

                # Capture similarity score, formatted to 2 decimal places
                if 'similarity_score' in df.columns:
                    display_df['similarity_score'] = df['similarity_score'].map(lambda x: f"{float(x):.2f}")

                # Create "cropped image" column with the HTML image
                if 'cropped_image' in df.columns:
                    display_df['cropped image'] = df['cropped_image'].map(img_html)

                # Save the modified CSV
                display_df.to_csv(image_csv, index=False)

                # Generate improved HTML with same format as regular results
                if not display_df.empty:
                    table_html = display_df.to_html(classes="custom-table table-striped", escape=False, index=False, border=0)

                    # Create a complete HTML file with proper styling
                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Match Results</title>
                        <style>
                            body {{ font-family: 'Arial', sans-serif; margin: 20px; }}
                            h1 {{ color: #333; }}
                            .custom-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                            .custom-table th {{ background-color: #f2f2f2; padding: 10px; text-align: left; border-bottom: 2px solid #ddd; }}
                            .custom-table td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                            .custom-table tr:hover {{ background-color: rgba(0,0,0,0.05); }}
                            .table-striped tbody tr:nth-of-type(odd) {{ background-color: rgba(0,0,0,0.02); }}
                            @media print {{
                                .custom-table {{ page-break-inside: avoid; }}
                                img {{ max-width: 80px; }}
                            }}
                        </style>
                    </head>
                    <body>
                        <h1>Component Match Results</h1>
                        <p>Image: {os.path.basename(image_path)}</p>
                        <p>Batch ID: {batch_id}</p>
                        <p>Processing date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        {table_html}
                    </body>
                    </html>
                    """

                    # Save the HTML file
                    with open(image_html, 'w') as f:
                        f.write(html_content)

        except Exception as e:
            logger.error(f"Error processing CSV/HTML for consistent format: {str(e)}")

        # Update status to completed
        batch_status[batch_id]['images'][image_index]['status'] = 'completed'
        batch_status[batch_id]['images'][image_index]['end_time'] = time.time()
        batch_status[batch_id]['images'][image_index]['result_dir'] = image_result_dir

        # Save results paths
        batch_status[batch_id]['images'][image_index]['csv_path'] = image_csv
        batch_status[batch_id]['images'][image_index]['html_path'] = image_html

        return True

    except Exception as e:
        logger.error(f"Error processing image {image_path}: {str(e)}")
        batch_status[batch_id]['images'][image_index]['status'] = 'failed'
        batch_status[batch_id]['images'][image_index]['error'] = str(e)
        return False

def batch_processor_thread():
    """Background thread for batch processing"""
    while True:
        try:
            # Get the next batch from queue
            batch_id = batch_queue.get()
            if not batch_id or batch_id not in batch_status:
                batch_queue.task_done()
                continue

            logger.debug(f"Processing batch: {batch_id}")

            # Update batch status
            batch_status[batch_id]['status'] = 'processing'
            batch_status[batch_id]['start_time'] = time.time()

            # Process each image in the batch
            success_count = 0
            total_images = len(batch_status[batch_id]['images'])

            for i, image_info in enumerate(batch_status[batch_id]['images']):
                if image_info['status'] != 'pending':
                    continue

                # Update overall progress
                batch_status[batch_id]['current_image'] = i
                batch_status[batch_id]['progress'] = int((i / total_images) * 100)

                # Process this image
                success = process_single_image(
                    image_info['path'], 
                    batch_id, 
                    i
                )

                if success:
                    success_count += 1

            # Update final status
            batch_status[batch_id]['end_time'] = time.time()
            batch_status[batch_id]['progress'] = 100
            batch_status[batch_id]['success_count'] = success_count

            if success_count == total_images:
                batch_status[batch_id]['status'] = 'completed'
            elif success_count == 0:
                batch_status[batch_id]['status'] = 'failed'
            else:
                batch_status[batch_id]['status'] = 'partial'

            logger.debug(f"Batch {batch_id} completed: {success_count}/{total_images} successful")

        except Exception as e:
            logger.error(f"Error in batch processor thread: {str(e)}")
        finally:
            batch_queue.task_done()

def start_batch_processor():
    """Start the batch processor thread"""
    thread = Thread(target=batch_processor_thread, daemon=True)
    thread.start()
    logger.debug("Batch processor thread started")

def create_batch(image_paths):
    """Create a new batch from the given image paths"""
    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create a clean directory for this batch
    batch_dir = clean_batch_directory(batch_id)

    # Initialize batch status
    batch_status[batch_id] = {
        'id': batch_id,
        'status': 'pending',
        'created': time.time(),
        'start_time': None,
        'end_time': None,
        'progress': 0,
        'current_image': 0,
        'success_count': 0,
        'images': []
    }

    # Copy images to batch directory and add to status
    for i, src_path in enumerate(image_paths):
        # Get the filename from the path
        filename = os.path.basename(src_path)
        dst_path = os.path.join(batch_dir, filename)

        # Copy the image
        shutil.copy2(src_path, dst_path)

        # Add to batch status
        batch_status[batch_id]['images'].append({
            'index': i,
            'original_path': src_path,
            'path': dst_path,
            'filename': filename,
            'status': 'pending',
            'start_time': None,
            'end_time': None,
            'error': None,
            'result_dir': None,
            'csv_path': None,
            'html_path': None
        })

    # Add to queue for processing
    batch_queue.put(batch_id)

    return batch_id

def get_batch_status(batch_id):
    """Get the status of a batch"""
    if batch_id not in batch_status:
        return None
    return batch_status[batch_id]

def get_all_batches():
    """Get all batches status"""
    return batch_status

def save_batch_status():
    """Save batch status to disk"""
    with open(os.path.join(BASE_DIR, 'batch_status.pkl'), 'wb') as f:
        pickle.dump(batch_status, f)

def load_batch_status():
    """Load batch status from disk"""
    status_path = os.path.join(BASE_DIR, 'batch_status.pkl')
    if os.path.exists(status_path):
        with open(status_path, 'rb') as f:
            global batch_status
            batch_status = pickle.load(f)

# Start the batch processor thread when module is imported
start_batch_processor()