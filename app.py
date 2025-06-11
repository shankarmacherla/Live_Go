from flask import Flask, request, render_template, send_file, redirect, url_for, jsonify
import os
import shutil
import subprocess
import pandas as pd
import logging
import time
import json
import base64
from datetime import datetime
from progress_tracker import progress_tracker


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key")

# --- Config Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEGMENT_OUTPUT_DIR = os.path.join(BASE_DIR, "static", "segmented_outputs")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
CROPPED_OUTPUT = os.path.join(BASE_DIR, "cropped_clip_data.pkl")
CATALOG_PATH = os.path.join(BASE_DIR, "all_categories_data.pkl")
METADATA_PATH = os.path.join(BASE_DIR, "metadata.pkl")
COMPARE_OUTPUT_CSV = os.path.join(BASE_DIR, "matched_results_by_category.csv")
COMPARE_OUTPUT_HTML = os.path.join(BASE_DIR,
                                   "matched_results_by_category.html")
# JSON conversion output
COMPARE_OUTPUT_JSON = os.path.join(BASE_DIR,
                                   "matched_catalog_results_top1.json")


# --- Clean segmented_outputs ---
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


# --- Home Page ---
@app.route("/", methods=["GET"])
def index():
    """Handle the home page"""
    # Clear uploads directory for a fresh start
    if os.path.exists(UPLOAD_DIR):
        for file in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        logger.debug("Cleared uploads directory for fresh start")
    return render_template("index.html")


# --- Auto Detection ---
@app.route("/detect", methods=["GET", "POST"])
def detect():
    """Handle automated detection"""
    if request.method == "POST":
        try:
            # Reset progress at start
            progress_tracker.reset_progress()
            progress_tracker.update_progress(5, "Starting image processing...")

            # Get the last uploaded image
            use_uploaded = request.form.get("use_uploaded") == "true"
            image_path = None

            if use_uploaded:
                # Find the most recent image in the uploads directory
                if not os.path.exists(UPLOAD_DIR):
                    logger.error("No uploads directory found")
                    return render_template(
                        "detect.html",
                        error=
                        "No uploaded image found. Please upload an image first."
                    ), 400

                # Get the most recent file in the uploads directory
                files = [
                    os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR)
                    if os.path.isfile(os.path.join(UPLOAD_DIR, f))
                ]
                if not files:
                    logger.error("No uploaded images found")
                    return render_template(
                        "detect.html",
                        error=
                        "No uploaded image found. Please upload an image first."
                    ), 400

                # Sort by most recent (using modified time for better accuracy)
                files.sort(key=os.path.getmtime, reverse=True)
                image_path = files[0]

                # Validate the uploaded image format - accept all common image types
                allowed_extensions = {
                    '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif',
                    '.gif', '.svg'
                }
                file_ext = os.path.splitext(image_path.lower())[1]

                if file_ext not in allowed_extensions:
                    logger.error(f"Invalid uploaded file format: {file_ext}")
                    return render_template(
                        "detect.html",
                        error=
                        "Upload failed. Please upload a valid image file (JPG, PNG, WebP, BMP, TIFF, GIF, SVG)."
                    ), 400

                logger.debug(f"Using previously uploaded image: {image_path}")
                progress_tracker.update_progress(15,
                                                 "Image loaded successfully")
            else:
                # Handle direct upload (fallback)
                image = request.files.get("image")
                if not image:
                    logger.error("No image uploaded")
                    return render_template("detect.html",
                                           error="No image was uploaded"), 400

                # Validate image format - accept all common image types
                filename = image.filename or ""
                allowed_extensions = {
                    '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif',
                    '.gif', '.svg'
                }
                file_ext = os.path.splitext(filename.lower())[1]

                if file_ext not in allowed_extensions:
                    logger.error(f"Invalid file format: {file_ext}")
                    return render_template(
                        "detect.html",
                        error=
                        "Upload failed. Please upload a valid image file (JPG, PNG, WebP, BMP, TIFF, GIF, SVG)."
                    ), 400

                # Ensure we have a filename
                if not filename:
                    filename = f"uploaded_image_{int(time.time())}.jpg"

                os.makedirs(UPLOAD_DIR, exist_ok=True)
                image_path = os.path.join(UPLOAD_DIR, filename)
                image.save(image_path)
                logger.debug(f"Image saved to {image_path}")

            # --- Clean outputs and run segmentation on ONLY this image ---
            logger.debug("Cleaning previous outputs before segmentation")
            clean_segmented_outputs()
            progress_tracker.update_progress(
                25, "Preparing for component detection...")

            logger.debug(
                f"Starting segmentation process for image: {image_path}")
            progress_tracker.update_progress(
                35, "Detecting network components...")
            try:
                result = subprocess.run(["python", "segment.py", image_path],
                                        check=True,
                                        capture_output=True,
                                        text=True,
                                        encoding='utf-8',
                                        errors='replace')
                logger.debug(f"Segmentation output: {result.stdout}")
                if result.stderr:
                    logger.warning(f"Segmentation warnings: {result.stderr}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Segmentation failed: {e}")
                logger.error(f"Error output: {e.stderr}")
                return render_template(
                    "detect.html",
                    error=f"Image processing failed during segmentation: {e}"
                ), 500

            # Check if segmentation produced any outputs
            if not os.path.exists(SEGMENT_OUTPUT_DIR) or not any(
                    os.listdir(SEGMENT_OUTPUT_DIR)):
                logger.warning("No components detected in the image")
                return render_template(
                    "detect.html",
                    error=
                    "No network components were detected in this image. Please try a different image with visible network equipment."
                ), 400

            progress_tracker.update_progress(
                55, "Components detected! Analyzing features...")

            # --- Generate cropped embeddings ---
            logger.debug("Generating cropped embeddings")
            try:
                result = subprocess.run([
                    "python", "cropped_embeddings.py", SEGMENT_OUTPUT_DIR,
                    CROPPED_OUTPUT
                ],
                                        check=True,
                                        capture_output=True,
                                        text=True)
                logger.debug(f"Embeddings output: {result.stdout}")
                if result.stderr:
                    logger.warning(f"Embeddings warnings: {result.stderr}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Embeddings generation failed: {e}")
                return render_template(
                    "detect.html",
                    error=f"Processing failed during embeddings generation: {e}"
                ), 500

            progress_tracker.update_progress(
                75, "Matching components with catalog...")

            # --- Run comparison ---
            logger.debug("Running comparison")
            try:
                result = subprocess.run([
                    "python", "comparision.py", CATALOG_PATH, CROPPED_OUTPUT,
                    METADATA_PATH, COMPARE_OUTPUT_CSV, COMPARE_OUTPUT_HTML
                ],
                                        check=True,
                                        capture_output=True,
                                        text=True)
                logger.debug(f"Comparison output: {result.stdout}")
                if result.stderr:
                    logger.warning(f"Comparison warnings: {result.stderr}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Comparison failed: {e}")
                return render_template(
                    "detect.html",
                    error=f"Processing failed during comparison: {e}"), 500

            # Verify that results were generated
            if not os.path.exists(COMPARE_OUTPUT_CSV):
                logger.error("CSV output file was not generated")
                return render_template(
                    "detect.html",
                    error=
                    "Processing completed but results file was not generated"
                ), 500

            progress_tracker.update_progress(95, "Finalizing results...")

            # Mark processing as complete
            progress_tracker.complete(
                "Processing completed successfully! Redirecting to results...")

            # Redirect to results page
            logger.debug("Processing complete, redirecting to results")
            return redirect(url_for("results"))
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            return render_template(
                "detect.html", error=f"Error processing image: {str(e)}"), 500

    return render_template("detect.html")


# --- Manual Detection ---
@app.route("/manual-detect", methods=["GET"])
def manual_detect():
    """Handle manual detection page"""
    return render_template("manual_detect.html")


# --- Save Manual Components ---
@app.route("/save-manual-components", methods=["POST"])
def save_manual_components():
    """Save manually detected components"""
    try:
        # Clean segmented outputs before processing new components
        clean_segmented_outputs()

        # Process all component files
        components_count = 0
        saved_components = []

        # Find all component files in the request
        for key in request.files:
            if key.startswith('component_'):
                components_count += 1

                # Get component type from form data
                index = key.split('_')[1]
                component_type = request.form.get(f"component_{index}_type",
                                                  "unknown")

                # Save the component image in a type-specific folder
                component_file = request.files[key]
                component_filename = f"{component_type}_{index}_{component_file.filename}"

                # Create type-specific directory if it doesn't exist
                type_dir = os.path.join(SEGMENT_OUTPUT_DIR, component_type)
                os.makedirs(type_dir, exist_ok=True)

                component_path = os.path.join(type_dir, component_filename)
                component_file.save(component_path)

                saved_components.append({
                    "path": component_path,
                    "type": component_type
                })

                logger.debug(f"Saved manual component: {component_path}")

        if components_count == 0:
            return {
                "success": False,
                "error": "No components found in request"
            }, 400

        # Generate cropped embeddings
        logger.debug("Generating cropped embeddings for manual components")
        subprocess.run([
            "python", "cropped_embeddings.py", SEGMENT_OUTPUT_DIR,
            CROPPED_OUTPUT
        ],
                       check=True)

        # Run comparison
        logger.debug("Running comparison for manual components")
        subprocess.run([
            "python", "comparision.py", CATALOG_PATH, CROPPED_OUTPUT,
            METADATA_PATH, COMPARE_OUTPUT_CSV, COMPARE_OUTPUT_HTML
        ],
                       check=True)

        return {
            "success": True,
            "message": f"Saved {components_count} components"
        }

    except Exception as e:
        logger.error(f"Error saving manual components: {str(e)}")
        return {"success": False, "error": str(e)}, 500


# --- Components Page ---
@app.route("/components")
def components():
    """Handle the components page - show only cropped images"""
    try:
        # Load cropped images from segmented_outputs
        cropped_images = []
        for root, dirs, files in os.walk(SEGMENT_OUTPUT_DIR):
            for file in files:
                if file.lower().endswith(('.jpg', '.png', '.jpeg', '.webp')):
                    # Determine component type from folder structure or filename
                    if os.path.basename(root) in [
                            'switch', 'port', 'cable', 'rack'
                    ]:
                        # Type is the folder name
                        component_type = os.path.basename(root)
                    elif "_" in file:
                        # Extract type from filename as fallback
                        component_type = file.split('_')[0]
                    else:
                        component_type = "unknown"

                    rel_path = os.path.relpath(os.path.join(root, file),
                                               BASE_DIR)
                    cropped_images.append({
                        "path": rel_path.replace("\\", "/"),
                        "type": component_type
                    })

        logger.debug(f"Found {len(cropped_images)} cropped images")

        # Group images by type for better organization
        grouped_images = {
            'switch': [],
            'port': [],
            'cable': [],
            'rack': [],
            'unknown': []
        }

        for img in cropped_images:
            if img['type'] in grouped_images:
                grouped_images[img['type']].append(img)
            else:
                grouped_images['unknown'].append(img)

        return render_template("components.html",
                               cropped_images=cropped_images,
                               grouped_images=grouped_images)
    except Exception as e:
        logger.error(f"Error displaying components: {str(e)}")
        return render_template(
            "index.html", error=f"Error displaying components: {str(e)}"), 500


# --- Results Page ---
@app.route("/results")
def results():
    """Handle the results page - showing only CSV data"""
    try:
        # Load comparison CSV
        table_html = None
        if os.path.exists(COMPARE_OUTPUT_CSV):
            df = pd.read_csv(COMPARE_OUTPUT_CSV, keep_default_na=False)

            # Allow all entries including duplicates - no filtering by similarity score

            # Fix image paths in the CSV to ensure they match the actual filesystem
            # Our folder structure is lowercase but CSV might have uppercase

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
                        path = path.replace(
                            f'/segmented_outputs/{component}/',
                            f'/segmented_outputs/{component.lower()}/')

                return path

            # Fix paths in the main data columns
            if 'cropped_image' in df.columns:
                df['cropped_image'] = df['cropped_image'].apply(fix_path)

            # Function to create HTML image tag with fallback
            def img_html(path):
                if not path or path == 'nan':
                    return ''

                # Make sure path has the correct separator for web display
                if isinstance(path, str):
                    path = path.replace('\\', '/')

                return f'<img src="{path}" alt="Component" style="width: 100px; height: auto; border-radius: 4px;" onerror="this.onerror=null; this.src=\'/static/images/image-not-found.svg\'; this.alt=\'Image not found\'" />'

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
                display_df['similarity_score'] = df['similarity_score'].apply(
                    lambda x: f"{float(x):.2f}")

            # Create "cropped image" column with the HTML image
            if 'cropped_image' in df.columns:
                display_df['cropped image'] = df['cropped_image'].apply(
                    img_html)

            # Add single coordinates column
            if 'coordinates' in df.columns:
                display_df['coordinates'] = df['coordinates']

            # Log which columns are available for debugging
            logger.debug(f"Original CSV columns: {df.columns.tolist()}")
            logger.debug(f"Display columns: {display_df.columns.tolist()}")

            # Improve table styling for better readability
            if not display_df.empty:
                # Generate table with improved styling
                table_html = display_df.to_html(
                    classes="custom-table table-striped",
                    escape=False,
                    index=False,
                    border=0)
            else:
                logger.warning("No data in CSV after filtering")
        else:
            logger.warning("CSV results file not found")
            df = pd.DataFrame()

        return render_template("results.html", table=table_html)
    except Exception as e:
        logger.error(f"Error displaying results: {str(e)}")
        return render_template(
            "index.html", error=f"Error displaying results: {str(e)}"), 500


# --- Image Enhancement ---
@app.route("/save-enhanced-image", methods=["POST"])
def save_enhanced_image():
    """Save an enhanced image"""
    try:
        enhanced_image_data = request.form.get('enhanced_image')
        original_path = request.form.get('original_path')

        if not enhanced_image_data or not original_path:
            return jsonify({
                "success": False,
                "error": "Missing required data"
            }), 400

        # Validate original path is within allowed directories
        full_original_path = os.path.join(BASE_DIR, original_path)
        if not os.path.normpath(full_original_path).startswith(
                os.path.normpath(SEGMENT_OUTPUT_DIR)):
            return jsonify({
                "success": False,
                "error": "Invalid original path"
            }), 400

        # Process the data URL
        format, imgstr = enhanced_image_data.split(';base64,')
        ext = format.split('/')[-1]
        data = base64.b64decode(imgstr)

        # Save the enhanced image
        with open(full_original_path, 'wb') as f:
            f.write(data)

        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"Error saving enhanced image: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# --- Component Management ---
@app.route("/component_info")
def component_info():
    """Get information about a component image"""
    try:
        # Check for network visualization parameters first (type, name)
        component_type = request.args.get('type')
        component_name = request.args.get('name')

        # If we have type and name, find the component image
        if component_type and component_name:
            # Look for images matching this component type and name
            logger.debug(
                f"Looking for component with type={component_type}, name={component_name}"
            )

            # Directory for this component type - try both original case and lowercase
            type_dir_lowercase = os.path.join(SEGMENT_OUTPUT_DIR,
                                              component_type.lower())
            type_dir_original = os.path.join(SEGMENT_OUTPUT_DIR,
                                             component_type)

            logger.debug(
                f"Looking for component in directories: {type_dir_lowercase} or {type_dir_original}"
            )

            # Search all segmented outputs directories for matching images
            matching_images = []
            for root, dirs, files in os.walk(SEGMENT_OUTPUT_DIR):
                for file in files:
                    if file.lower().endswith(
                        ('.jpg', '.png', '.jpeg', '.webp')):
                        # Check if the filename or parent directory matches our component type or name
                        if (component_type.lower() in file.lower()
                                or component_type.lower()
                                in os.path.basename(root).lower()
                                or component_name.lower() in file.lower()):
                            rel_path = os.path.relpath(
                                os.path.join(root, file), BASE_DIR)
                            matching_images.append(rel_path.replace("\\", "/"))

                if matching_images:
                    # Use the first matching image
                    image_path = matching_images[0]

                    # Get image details
                    full_path = os.path.join(BASE_DIR, image_path)

                    try:
                        # Get file size
                        size_bytes = os.path.getsize(full_path)
                        if size_bytes < 1024:
                            size = f"{size_bytes} bytes"
                        elif size_bytes < 1024 * 1024:
                            size = f"{size_bytes / 1024:.1f} KB"
                        else:
                            size = f"{size_bytes / (1024 * 1024):.1f} MB"

                        # Get image dimensions
                        from PIL import Image
                        with Image.open(full_path) as img:
                            dimensions = f"{img.width}x{img.height} pixels"

                        return jsonify({
                            "success": True,
                            "path": image_path,
                            "size": size,
                            "dimensions": dimensions,
                            "details": {
                                "type":
                                component_type,
                                "name":
                                component_name,
                                "category":
                                os.path.basename(os.path.dirname(full_path))
                            }
                        })
                    except Exception as e:
                        logger.error(f"Error getting image details: {str(e)}")

                # If no matching image, try using a sample for the component type
                sample_images = {
                    "rack": "static/images/samples/rack.jpg",
                    "switch": "static/images/samples/switch.jpg",
                    "port": "static/images/samples/port.jpg",
                    "cable": "static/images/samples/cable.jpg"
                }

                if component_type.lower() in sample_images:
                    sample_path = sample_images[component_type.lower()]
                    if os.path.exists(os.path.join(BASE_DIR, sample_path)):
                        return jsonify({
                            "success": True,
                            "path": sample_path,
                            "details": {
                                "type": component_type,
                                "name": component_name,
                                "note": "Sample image - no exact match found"
                            }
                        })

                # Still no match, check for any image of this type
                for root, dirs, files in os.walk(SEGMENT_OUTPUT_DIR):
                    if os.path.basename(
                            root).lower() == component_type.lower():
                        for file in files:
                            if file.lower().endswith(
                                ('.jpg', '.png', '.jpeg', '.webp')):
                                rel_path = os.path.relpath(
                                    os.path.join(root, file), BASE_DIR)
                                return jsonify({
                                    "success":
                                    True,
                                    "path":
                                    rel_path.replace("\\", "/"),
                                    "details": {
                                        "type":
                                        component_type,
                                        "name":
                                        component_name,
                                        "note":
                                        "Similar component image - no exact match found"
                                    }
                                })

                # If all else fails, return a not found error for this component
                return jsonify({
                    "success":
                    False,
                    "error":
                    f"No image found for {component_type} named {component_name}"
                }), 404

            # Try both directory options
            type_dirs = [type_dir_lowercase, type_dir_original]
            matching_images = []

            for type_dir in type_dirs:
                if os.path.exists(type_dir):
                    for file in os.listdir(type_dir):
                        if file.lower().endswith(
                            ('.jpg', '.png', '.jpeg', '.webp')):
                            # Check if filename contains the component name
                            if component_name.lower() in file.lower():
                                rel_path = os.path.relpath(
                                    os.path.join(type_dir, file), BASE_DIR)
                                matching_images.append(
                                    rel_path.replace("\\", "/"))

            if matching_images:
                # Use the first matching image
                image_path = matching_images[0]

                # Get image details
                full_path = os.path.join(BASE_DIR, image_path)

                try:
                    # Get file size
                    size_bytes = os.path.getsize(full_path)
                    if size_bytes < 1024:
                        size = f"{size_bytes} bytes"
                    elif size_bytes < 1024 * 1024:
                        size = f"{size_bytes / 1024:.1f} KB"
                    else:
                        size = f"{size_bytes / (1024 * 1024):.1f} MB"

                    # Get image dimensions
                    from PIL import Image
                    with Image.open(full_path) as img:
                        dimensions = f"{img.width}x{img.height} pixels"

                    return jsonify({
                        "success": True,
                        "path": image_path,
                        "size": size,
                        "dimensions": dimensions,
                        "details": {
                            "type": component_type,
                            "name": component_name
                        }
                    })
                except Exception as e:
                    logger.error(f"Error getting image details: {str(e)}")

            # If no matching image, return the first image of this type
            # Check both directory options
            for type_dir in type_dirs:
                if os.path.exists(type_dir):
                    for file in os.listdir(type_dir):
                        if file.lower().endswith(
                            ('.jpg', '.png', '.jpeg', '.webp')):
                            rel_path = os.path.relpath(
                                os.path.join(type_dir, file), BASE_DIR)
                            return jsonify({
                                "success": True,
                                "path": rel_path.replace("\\", "/"),
                                "details": {
                                    "type":
                                    component_type,
                                    "name":
                                    component_name,
                                    "note":
                                    "Similar component image - no exact match found"
                                }
                            })

            # If still no match, return error
            return jsonify({
                "success":
                False,
                "error":
                f"No image found for {component_type} named {component_name}"
            }), 404

        # Fallback to original implementation with direct path
        path = request.args.get('path')
        if not path:
            return jsonify({
                "success": False,
                "error": "No path specified"
            }), 400

        full_path = os.path.join(BASE_DIR, path)

        # Security check to make sure the path is within our segmented outputs
        if not os.path.normpath(full_path).startswith(
                os.path.normpath(SEGMENT_OUTPUT_DIR)):
            return jsonify({"success": False, "error": "Invalid path"}), 400

        # Get file information
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            return jsonify({"success": False, "error": "File not found"}), 404

        try:
            # Get file size
            size_bytes = os.path.getsize(full_path)
            if size_bytes < 1024:
                size = f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                size = f"{size_bytes / 1024:.1f} KB"
            else:
                size = f"{size_bytes / (1024 * 1024):.1f} MB"

            # Get file creation/modification time
            created = datetime.fromtimestamp(
                os.path.getctime(full_path)).strftime('%Y-%m-%d %H:%M:%S')

            # Get image dimensions
            try:
                from PIL import Image
                with Image.open(full_path) as img:
                    dimensions = f"{img.width}x{img.height} pixels"
            except Exception as e:
                logger.error(f"Error getting image dimensions: {str(e)}")
                dimensions = "Unknown"

            return jsonify({
                "success": True,
                "path": path,
                "size": size,
                "created": created,
                "dimensions": dimensions,
                "type": os.path.basename(os.path.dirname(full_path))
            })

        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return jsonify({
                "success": True,
                "path": path,
                "size": "Unknown",
                "created": "Unknown",
                "dimensions": "Unknown"
            })

    except Exception as e:
        logger.error(f"Error getting component info: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/delete_component", methods=["POST"])
def delete_component():
    """Delete a single component image"""
    try:
        data = request.get_json()

        if not data or "path" not in data:
            return jsonify({
                "success": False,
                "error": "No path specified"
            }), 400

        path = data["path"]
        full_path = os.path.join(BASE_DIR, path)

        # Security check to make sure the path is within our segmented outputs
        if not os.path.normpath(full_path).startswith(
                os.path.normpath(SEGMENT_OUTPUT_DIR)):
            return jsonify({"success": False, "error": "Invalid path"}), 400

        # Delete the file if it exists
        if os.path.exists(full_path) and os.path.isfile(full_path):
            os.remove(full_path)
            logger.info(f"Deleted component: {path}")
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "File not found"}), 404

    except Exception as e:
        logger.error(f"Error deleting component: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/delete_components", methods=["POST"])
def delete_components():
    """Delete multiple component images"""
    try:
        data = request.get_json()

        if not data or "paths" not in data or not isinstance(
                data["paths"], list):
            return jsonify({
                "success": False,
                "error": "No paths specified"
            }), 400

        paths = data["paths"]
        deleted_count = 0

        for path in paths:
            full_path = os.path.join(BASE_DIR, path)

            # Security check to make sure the path is within our segmented outputs
            if not os.path.normpath(full_path).startswith(
                    os.path.normpath(SEGMENT_OUTPUT_DIR)):
                continue

            # Delete the file if it exists
            if os.path.exists(full_path) and os.path.isfile(full_path):
                os.remove(full_path)
                deleted_count += 1
                logger.info(f"Deleted component: {path}")

        return jsonify({
            "success": True,
            "deleted_count": deleted_count,
            "total": len(paths)
        })

    except Exception as e:
        logger.error(f"Error deleting components: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# --- Analytics Dashboard has been removed ---

# --- JSON Functionality Removed ---


# --- CSV Download ---
@app.route("/download_csv")
def download_csv():
    """Handle CSV download with filtered columns and similarity score > 0.7"""
    try:
        if not os.path.exists(COMPARE_OUTPUT_CSV):
            logger.error("CSV file not found for download")
            return "CSV not found", 404

        # Load the CSV data
        df = pd.read_csv(COMPARE_OUTPUT_CSV, keep_default_na=False)

        # Allow all entries including duplicates - no filtering by similarity score

        # Fix file paths for cropped_image
        def fix_path(path):
            if isinstance(path, str) and "segmented_outputs" in path:
                # Fix path separators - ensure forward slashes
                path = path.replace('\\', '/')

                # If path doesn't include the leading slash add it
                if not path.startswith('/'):
                    path = '/' + path

                # Fix case sensitivity in component type directories
                for component in ['Cable', 'Rack', 'Switch', 'Port']:
                    path = path.replace(
                        f'/segmented_outputs/{component}/',
                        f'/segmented_outputs/{component.lower()}/')

            return path

        # Fix paths in the main data columns
        if 'cropped_image' in df.columns:
            df['cropped_image'] = df['cropped_image'].apply(fix_path)

        # Create filtered DataFrame with only the required columns
        filtered_df = pd.DataFrame()

        # Map old column names to new ones
        column_mapping = {
            'category': 'category',
            'name': 'name',
            'description': 'description',
            'similarity_score': 'similarityscore',
            'cropped_image': 'cropped image',
            'coordinates': 'coordinates'
        }

        # Extract and rename columns as specified
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                # For similarity score, format to 2 decimal places
                if old_name == 'similarity_score':
                    filtered_df[new_name] = df[old_name].apply(
                        lambda x: f"{float(x):.2f}")
                else:
                    filtered_df[new_name] = df[old_name]

        # Create a temporary file for the filtered CSV
        temp_csv_path = os.path.join(BASE_DIR, "filtered_results.csv")
        filtered_df.to_csv(temp_csv_path, index=False)

        # Return the filtered CSV file for download
        return send_file(temp_csv_path,
                         as_attachment=True,
                         download_name="matched_results.csv")
    except Exception as e:
        logger.error(f"Error downloading CSV: {str(e)}")
        return f"Error downloading CSV: {str(e)}", 500


# --- HTML Download with Embedded Images ---
@app.route("/download_html")
def download_html():
    """Handle HTML download with embedded images"""
    try:
        # Check if the CSV file exists
        if os.path.exists(COMPARE_OUTPUT_CSV):
            logger.debug(
                f"Generating HTML from CSV file: {COMPARE_OUTPUT_CSV}")

            # Load the CSV data
            df = pd.read_csv(COMPARE_OUTPUT_CSV, keep_default_na=False)

            # Filter to only keep rows with similarity score > 0.7
            if 'similarity_score' in df.columns:
                df = df[df['similarity_score'] > 0.7]

            # Function to convert image to base64 for direct embedding in HTML
            def img_to_base64_html(path):
                if not path or path == '':
                    return 'No image'

                # Convert web path to file system path
                if path.startswith('/'):
                    file_path = os.path.join(BASE_DIR,
                                             path[1:])  # Remove leading slash
                else:
                    file_path = os.path.join(BASE_DIR, path)

                # Check if file exists
                if not os.path.exists(file_path):
                    logger.warning(f"Image file not found: {file_path}")
                    # Return placeholder image or text
                    return '<span style="color: #999;">Image not available</span>'

                # Read the image file and convert to base64
                try:
                    with open(file_path, 'rb') as img_file:
                        img_data = img_file.read()

                    # Get the image format from the file extension
                    img_format = os.path.splitext(file_path)[1].lstrip('.')
                    if img_format.lower() in ['jpg', 'jpeg']:
                        img_format = 'jpeg'
                    elif img_format.lower() in ['png']:
                        img_format = 'png'
                    else:
                        img_format = 'jpeg'  # Default format

                    # Convert to base64
                    import base64
                    encoded = base64.b64encode(img_data).decode('utf-8')
                    img_src = f"data:image/{img_format};base64,{encoded}"
                    return f'<img src="{img_src}" class="component-image" alt="Component">'
                except Exception as e:
                    logger.error(f"Error encoding image {file_path}: {str(e)}")
                    return '<span style="color: #999;">Error loading image</span>'

            # Create HTML table rows
            table_rows = ""
            for _, row in df.iterrows():
                category = row.get('category', 'Unknown')
                name = row.get('name', '')
                description = row.get('description', '')
                similarity = row.get('similarity_score', 0)
                cropped_img = row.get('cropped_image', '')

                # Format similarity score
                if isinstance(similarity, (int, float)):
                    similarity_formatted = f"{float(similarity):.2f}"
                else:
                    similarity_formatted = similarity

                # Add row to HTML with base64 embedded image
                table_rows += f"""
                <tr>
                    <td>{img_to_base64_html(cropped_img)}</td>
                    <td>{category}</td>
                    <td>{name}</td>
                    <td>{description}</td>
                    <td>{similarity_formatted}</td>
                </tr>
                """

            # Create the complete HTML document
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Network Component Analysis Results</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f8f9fa;
                    }}
                    h1 {{
                        text-align: center;
                        color: #0066cc;
                        margin-bottom: 20px;
                    }}
                    .timestamp {{
                        text-align: center;
                        color: #6c757d;
                        margin-bottom: 30px;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        background-color: white;
                        box-shadow: 0 2px 3px rgba(0,0,0,0.1);
                        border-radius: 5px;
                        overflow: hidden;
                        margin-bottom: 30px;
                    }}
                    th, td {{
                        padding: 12px 15px;
                        text-align: left;
                        border-bottom: 1px solid #ddd;
                    }}
                    th {{
                        background-color: #0066cc;
                        color: white;
                        font-weight: bold;
                    }}
                    tr:hover {{
                        background-color: #f5f5f5;
                    }}
                    .component-image {{
                        border: 1px solid #ddd;
                        border-radius: 4px;
                        padding: 3px;
                        max-width: 150px;
                        height: auto;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 30px;
                        color: #6c757d;
                        font-size: 0.9em;
                    }}
                    .note {{
                        margin-top: 30px;
                        padding: 15px;
                        background-color: #f0f7ff;
                        border-left: 4px solid #0066cc;
                        border-radius: 4px;
                    }}
                </style>
            </head>
            <body>
                <h1>Network Component Analysis Results</h1>
                <div class="timestamp">Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>

                <table>
                    <thead>
                        <tr>
                            <th>Component Image</th>
                            <th>Category</th>
                            <th>Name</th>
                            <th>Description</th>
                            <th>Similarity Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>

                <div class="note">
                    <p><strong>Note:</strong> All component images are embedded directly in this HTML file for easy sharing and viewing without needing the original server environment.</p>
                </div>

                <div class="footer">
                    <p>Generated by Network Component Analysis System</p>
                </div>
            </body>
            </html>
            """

            # Save the HTML to a file
            html_output_path = os.path.join(BASE_DIR, "network_results.html")
            with open(html_output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Return the HTML file for download
            return send_file(html_output_path,
                             as_attachment=True,
                             download_name="network_component_results.html")
        else:
            # If the CSV file doesn't exist, tell the user to process some data first
            logger.error(f"CSV file not found: {COMPARE_OUTPUT_CSV}")
            return "No comparison results available. Please process an image first.", 404

    except Exception as e:
        logger.error(f"Error generating HTML: {str(e)}")
        return f"Error generating HTML: {str(e)}", 500


# --- Progress API ---
@app.route("/api/progress")
def get_progress():
    """API endpoint to get current processing progress"""
    return jsonify(progress_tracker.get_progress())


# --- Batch Processing Routes ---

# Import batch processor module
import batch_processor
from datetime import datetime
import zipfile
import io

# Initialize batch processing paths
BATCH_UPLOAD_DIR = os.path.join(BASE_DIR, "batch_uploads")
BATCH_RESULTS_DIR = os.path.join(BASE_DIR, "static", "batch_results")


# Jinja2 filters for batch processing
@app.template_filter('timestamp_to_datetime')
def timestamp_to_datetime(timestamp):
    """Convert timestamp to formatted datetime string"""
    if not timestamp:
        return "N/A"
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


@app.template_filter('format_duration')
def format_duration(seconds):
    """Format duration in seconds to human-readable format"""
    if not seconds:
        return "N/A"

    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


@app.template_filter('tojson')
def filter_tojson(obj):
    """Convert object to JSON string"""
    return json.dumps(obj)


# Batch Processing Page
@app.route("/batch_process")
def batch_process():
    """Handle the batch processing page"""
    return render_template("batch_process.html")


# Create a new batch
@app.route("/create_batch", methods=["POST"])
def create_batch():
    """Create a new batch of images for processing"""
    try:
        # Get images from request
        images = request.files.getlist("images")

        if not images:
            logger.error("No images found in request")
            return jsonify({
                "success": False,
                "error": "No images uploaded"
            }), 400

        # Create directory for uploaded images if it doesn't exist
        os.makedirs(BATCH_UPLOAD_DIR, exist_ok=True)

        # Save images to batch uploads directory
        image_paths = []
        for image in images:
            if image and image.filename:
                # Ensure filename is secure
                filename = f"{int(time.time())}_{image.filename}"
                image_path = os.path.join(BATCH_UPLOAD_DIR, filename)

                # Save image
                image.save(image_path)
                image_paths.append(image_path)
                logger.debug(f"Saved batch image to {image_path}")

        if not image_paths:
            logger.error("No valid images found in request")
            return jsonify({
                "success": False,
                "error": "No valid images uploaded"
            }), 400

        # Create batch in batch processor
        batch_id = batch_processor.create_batch(image_paths)
        logger.debug(
            f"Created batch {batch_id} with {len(image_paths)} images")

        return jsonify({
            "success": True,
            "batch_id": batch_id,
            "image_count": len(image_paths)
        })

    except Exception as e:
        logger.error(f"Error creating batch: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# Get status of a specific batch
@app.route("/get_batch_status/<batch_id>")
def get_batch_status(batch_id):
    """Get the status of a specific batch"""
    try:
        # Get batch status from processor
        status = batch_processor.get_batch_status(batch_id)

        if not status:
            logger.error(f"Batch {batch_id} not found")
            return jsonify({"success": False, "error": "Batch not found"}), 404

        return jsonify({"success": True, "batch": status})

    except Exception as e:
        logger.error(f"Error getting batch status: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# Get all batches
@app.route("/get_all_batches")
def get_all_batches():
    """Get all batches status"""
    try:
        # Get all batches from processor
        batches = batch_processor.get_all_batches()

        return jsonify({"success": True, "batches": batches})

    except Exception as e:
        logger.error(f"Error getting all batches: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# Batch results page
@app.route("/batch_results/<batch_id>")
def batch_results(batch_id):
    """Show batch results page"""
    try:
        # Get batch status
        batch = batch_processor.get_batch_status(batch_id)

        if not batch:
            logger.error(f"Batch {batch_id} not found")
            return render_template("index.html", error="Batch not found"), 404

        # Add processing duration
        if batch['start_time'] and batch['end_time']:
            batch['duration'] = batch['end_time'] - batch['start_time']
        else:
            batch['duration'] = None

        # Count components per image
        total_components = 0
        total_matches = 0

        for image in batch['images']:
            if image['status'] == 'completed' and image['result_dir']:
                # Count components by type
                component_counts = {}

                for component_type in ['Cable', 'Port', 'Rack', 'Switch']:
                    type_dir = os.path.join(image['result_dir'],
                                            component_type)
                    if os.path.exists(type_dir):
                        count = len([
                            f for f in os.listdir(type_dir)
                            if os.path.isfile(os.path.join(type_dir, f))
                        ])
                        component_counts[component_type] = count
                        total_components += count

                # Set component counts
                image['component_counts'] = component_counts

                # Count matches from CSV
                if image['csv_path'] and os.path.exists(image['csv_path']):
                    try:
                        df = pd.read_csv(image['csv_path'])
                        if not df.empty and 'similarity_score' in df.columns:
                            # Count matches with similarity > 0.7
                            matches = len(df[df['similarity_score'] > 0.7])
                            image['match_count'] = matches
                            total_matches += matches
                    except Exception as csv_err:
                        logger.error(
                            f"Error reading CSV for match count: {str(csv_err)}"
                        )

        # Add component and match counts to batch
        batch['component_count'] = total_components
        batch['match_count'] = total_matches

        return render_template("batch_results.html", batch=batch)

    except Exception as e:
        logger.error(f"Error showing batch results: {str(e)}")
        return render_template(
            "index.html", error=f"Error showing batch results: {str(e)}"), 500


# Batch components page
@app.route("/batch_components/<batch_id>/<int:image_index>")
def batch_components(batch_id, image_index):
    """Show components for a specific image in a batch"""
    try:
        # Get batch status
        batch = batch_processor.get_batch_status(batch_id)

        if not batch or image_index >= len(batch['images']):
            logger.error(f"Batch {batch_id} or image {image_index} not found")
            return render_template("index.html",
                                   error="Batch or image not found"), 404

        # Get image info
        image_info = batch['images'][image_index]

        if image_info['status'] != 'completed' or not image_info['result_dir']:
            logger.error(
                f"Image {image_index} in batch {batch_id} not completed")
            return render_template("index.html",
                                   error="Image processing not completed"), 400

        # Get components
        components = []

        for component_type in ['Cable', 'Port', 'Rack', 'Switch']:
            type_dir = os.path.join(image_info['result_dir'], component_type)
            if os.path.exists(type_dir):
                for filename in os.listdir(type_dir):
                    if os.path.isfile(os.path.join(type_dir, filename)):
                        # Create relative path for web display
                        rel_path = os.path.join(
                            "static", "batch_results", batch_id,
                            os.path.basename(image_info['result_dir']),
                            component_type, filename)
                        rel_path = rel_path.replace("\\", "/")

                        # Get component ID from filename
                        component_id = os.path.splitext(filename)[0]

                        # Get image dimensions
                        try:
                            from PIL import Image
                            img_path = os.path.join(type_dir, filename)
                            with Image.open(img_path) as img:
                                width, height = img.size
                        except Exception:
                            width, height = 0, 0

                        # Add to components list
                        components.append({
                            "id": component_id,
                            "type": component_type,
                            "image_path": rel_path,
                            "width": width,
                            "height": height
                        })

        # Get match information if available
        if image_info['csv_path'] and os.path.exists(image_info['csv_path']):
            try:
                df = pd.read_csv(image_info['csv_path'])

                if not df.empty and 'cropped_image' in df.columns:
                    # Match components with CSV data
                    for component in components:
                        # Try to find this component in the CSV data
                        filename = os.path.basename(component['image_path'])

                        # Look for rows with this image
                        for _, row in df.iterrows():
                            csv_image = str(row.get('cropped_image', ''))

                            # If this CSV row is for this component
                            if filename in csv_image:
                                # Add match information
                                component['match'] = {
                                    "name": row.get('matched_name', 'Unknown'),
                                    "score":
                                    float(row.get('similarity_score', 0)),
                                    "model": row.get('model', ''),
                                    "manufacturer":
                                    row.get('manufacturer', '')
                                }
                                break
            except Exception as csv_err:
                logger.error(
                    f"Error reading CSV for match info: {str(csv_err)}")

        # Sort components by type
        components = sorted(components, key=lambda x: x['type'])

        return render_template("batch_components.html",
                               batch_id=batch_id,
                               image_index=image_index,
                               image_info=image_info,
                               components=components,
                               original_image=True)

    except Exception as e:
        logger.error(f"Error showing batch components: {str(e)}")
        return render_template(
            "index.html",
            error=f"Error showing batch components: {str(e)}"), 500


# Batch CSV results page
@app.route("/batch_results_csv/<batch_id>/<int:image_index>")
def batch_results_csv(batch_id, image_index):
    """Show CSV results for a specific image in a batch"""
    try:
        # Get batch status
        batch = batch_processor.get_batch_status(batch_id)

        if not batch or image_index >= len(batch['images']):
            logger.error(f"Batch {batch_id} or image {image_index} not found")
            return render_template("index.html",
                                   error="Batch or image not found"), 404

        # Get image info
        image_info = batch['images'][image_index]

        if image_info['status'] != 'completed' or not image_info[
                'csv_path'] or not os.path.exists(image_info['csv_path']):
            logger.error(
                f"CSV results for image {image_index} in batch {batch_id} not available"
            )
            return render_template("index.html",
                                   error="CSV results not available"), 400

        # Load CSV data and create table HTML in the same format as regular results
        table_html = None
        if os.path.exists(image_info['csv_path']):
            df = pd.read_csv(image_info['csv_path'], keep_default_na=False)

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
                        path = path.replace(
                            f'/segmented_outputs/{component}/',
                            f'/segmented_outputs/{component.lower()}/')

                return path

            # Function to create HTML image tag with fallback
            def img_html(path):
                if not path or path == 'nan':
                    return ''

                try:
                    # Make sure path has the correct separator for web display
                    if isinstance(path, str):
                        path = path.replace('\\', '/')

                        # If it's a batch component, adjust the path
                        if 'batch_results' not in path and os.path.exists(
                                image_info['result_dir']):
                            if os.path.basename(path) in path:
                                # This is a relative path, need to make it a web URL
                                component_type = None
                                for t in ['Cable', 'Port', 'Rack', 'Switch']:
                                    if t.lower() in path.lower():
                                        component_type = t
                                        break

                                if component_type:
                                    filename = os.path.basename(path)
                                    path = f"/static/batch_results/{batch_id}/{os.path.basename(image_info['result_dir'])}/{component_type}/{filename}"

                    # Convert image to base64 for embedding in HTML
                    import base64
                    from PIL import Image
                    import io

                    # Find the actual file path
                    full_path = None
                    path_to_check = path

                    # Check if the path is a web URL path
                    if path.startswith('/static/'):
                        path_to_check = os.path.join(
                            BASE_DIR, path[1:])  # Remove leading slash
                    else:
                        path_to_check = os.path.join(BASE_DIR, path)

                    # If file exists, use it
                    if os.path.exists(path_to_check):
                        full_path = path_to_check
                    else:
                        # If not, try to find the file in the results directory
                        # by matching the filename
                        filename = os.path.basename(path)
                        for component_type in [
                                'Cable', 'Port', 'Rack', 'Switch'
                        ]:
                            test_path = os.path.join(image_info['result_dir'],
                                                     component_type, filename)
                            if os.path.exists(test_path):
                                full_path = test_path
                                break

                    # If we still couldn't find the file, return a placeholder
                    if not full_path or not os.path.exists(full_path):
                        return f'<img src="" alt="Image not found" style="width: 100px; height: auto; border-radius: 4px;" />'

                    # Open image and convert to base64
                    img = Image.open(full_path)
                    buffered = io.BytesIO()
                    img.save(buffered, format=img.format or "JPEG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()

                    # Determine mimetype
                    mimetype = "image/jpeg"  # Default
                    if img.format:
                        if img.format.lower() == 'png':
                            mimetype = "image/png"
                        elif img.format.lower() == 'gif':
                            mimetype = "image/gif"
                        elif img.format.lower() in ('jpg', 'jpeg'):
                            mimetype = "image/jpeg"

                    # Return embedded image
                    return f'<img src="data:{mimetype};base64,{img_str}" alt="Component" style="width: 100px; height: auto; border-radius: 4px;" />'
                except Exception as e:
                    logger.error(f"Error embedding image {path}: {str(e)}")
                    return f'<img src="" alt="Error loading image" style="width: 100px; height: auto; border-radius: 4px;" />'

            # Improve table styling for better readability
            if not df.empty:
                # If 'cropped image' already exists, use it; otherwise create it
                if 'cropped image' not in df.columns and 'cropped_image' in df.columns:
                    df['cropped image'] = df['cropped_image'].apply(img_html)

                # Generate table with improved styling
                table_html = df.to_html(classes="custom-table table-striped",
                                        escape=False,
                                        index=False,
                                        border=0)
            else:
                logger.warning("No data in CSV after filtering")
        else:
            logger.warning("CSV results file not found")

        return render_template("batch_csv_results.html",
                               batch_id=batch_id,
                               image_index=image_index,
                               image_info=image_info,
                               table=table_html)

    except Exception as e:
        logger.error(f"Error showing batch CSV results: {str(e)}")
        return render_template(
            "index.html",
            error=f"Error showing batch CSV results: {str(e)}"), 500


# Download batch image CSV
@app.route("/download_batch_image_csv/<batch_id>/<int:image_index>")
def download_batch_image_csv(batch_id, image_index):
    """Download CSV results for a specific image in a batch"""
    try:
        # Get batch status
        batch = batch_processor.get_batch_status(batch_id)

        if not batch or image_index >= len(batch['images']):
            logger.error(f"Batch {batch_id} or image {image_index} not found")
            return "Batch or image not found", 404

        # Get image info
        image_info = batch['images'][image_index]

        if image_info['status'] != 'completed' or not image_info[
                'csv_path'] or not os.path.exists(image_info['csv_path']):
            logger.error(
                f"CSV results for image {image_index} in batch {batch_id} not available"
            )
            return "CSV results not available", 400

        # Return the CSV file for download
        return send_file(
            image_info['csv_path'],
            as_attachment=True,
            download_name=f"batch_{batch_id}_image_{image_index}_results.csv")

    except Exception as e:
        logger.error(f"Error downloading batch image CSV: {str(e)}")
        return f"Error downloading CSV: {str(e)}", 500


# Download complete batch results as zip
@app.route("/download_batch_results/<batch_id>")
def download_batch_results(batch_id):
    """Download all results for a batch as a zip file"""
    try:
        # Get batch status
        batch = batch_processor.get_batch_status(batch_id)

        if not batch:
            logger.error(f"Batch {batch_id} not found")
            return "Batch not found", 404

        # Create in-memory zip file
        memory_file = io.BytesIO()

        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add batch summary JSON
            zf.writestr('batch_summary.json', json.dumps(batch, indent=2))

            # Add all completed image results
            for i, image in enumerate(batch['images']):
                if image['status'] == 'completed' and image[
                        'result_dir'] and os.path.exists(image['result_dir']):
                    # Add original image
                    if os.path.exists(image['path']):
                        zf.write(image['path'],
                                 f"images/image_{i}_original.jpg")

                    # Add CSV results
                    if image['csv_path'] and os.path.exists(image['csv_path']):
                        zf.write(image['csv_path'],
                                 f"results/image_{i}_results.csv")

                    # Add HTML results
                    if image['html_path'] and os.path.exists(
                            image['html_path']):
                        zf.write(image['html_path'],
                                 f"results/image_{i}_results.html")

                    # Add all component images
                    for component_type in ['Cable', 'Port', 'Rack', 'Switch']:
                        type_dir = os.path.join(image['result_dir'],
                                                component_type)
                        if os.path.exists(type_dir):
                            for filename in os.listdir(type_dir):
                                file_path = os.path.join(type_dir, filename)
                                if os.path.isfile(file_path):
                                    zf.write(
                                        file_path,
                                        f"components/image_{i}/{component_type}/{filename}"
                                    )

        # Rewind the file for reading
        memory_file.seek(0)

        # Return the zip file
        return send_file(memory_file,
                         as_attachment=True,
                         download_name=f"batch_{batch_id}_results.zip",
                         mimetype="application/zip")

    except Exception as e:
        logger.error(f"Error downloading batch results: {str(e)}")
        return f"Error downloading batch results: {str(e)}", 500


# --- End of Application Routes ---



if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(SEGMENT_OUTPUT_DIR, exist_ok=True)
    os.makedirs(BATCH_UPLOAD_DIR, exist_ok=True)
    os.makedirs(BATCH_RESULTS_DIR, exist_ok=True)

    # Load batch status if available
    batch_processor.load_batch_status()

    # Run the app
    app.run(host="0.0.0.0", port=5000, debug=True)
