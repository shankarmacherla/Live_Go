import os
import sys
import cv2
import json
import numpy as np
from ultralytics import YOLO

# --- Configuration ---
GENERAL_MODEL_PATH = "best.pt"         # For Cable, Switch, Rack, Fuse
PORTS_MODEL_PATH = "port_best.pt"      # For Port detection
OUTPUT_DIR = "static/segmented_outputs"
CONF_THRESHOLD = 0.2
COORDINATES_FILE = "static/segmented_outputs/coordinates.json"
MARGIN = 10           # Extra padding in pixels
MIN_DIM = 128         # Minimum dimension for clarity

# --- Input Validation ---
if len(sys.argv) < 2:
    print("❌ Please provide input image path.")
    sys.exit(1)

IMAGE_PATH = sys.argv[1]
img = cv2.imread(IMAGE_PATH)
if img is None:
    raise FileNotFoundError(f"Image not found: {IMAGE_PATH}")

# --- Define Class Mapping ---
TARGET_CLASS_MAP = {
    'Cable': 'Cable',
    'Port': 'Port',
    'Rack': 'Rack',
    'Switch': 'Switch',
    'fuse': 'Rack'
}

# --- Prepare Output Folders ---
for folder in set(TARGET_CLASS_MAP.values()):
    os.makedirs(os.path.join(OUTPUT_DIR, folder), exist_ok=True)

# --- Load Models ---
print("📦 Loading YOLO models...")
general_model = YOLO(GENERAL_MODEL_PATH)
port_model = YOLO(PORTS_MODEL_PATH)

# --- Detect General Components ---
print("🔍 Running general detection...")
general_results = general_model(img, conf=CONF_THRESHOLD, verbose=False)[0]
general_class_names = general_model.names

coordinates_data = {}
object_counter = 0
region_counter = 0

# --- Crop Utility ---
def crop_and_save(region, path):
    h, w = region.shape[:2]
    if h < MIN_DIM or w < MIN_DIM:
        region = cv2.resize(region, (max(w, MIN_DIM), max(h, MIN_DIM)), interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(path, region, [int(cv2.IMWRITE_JPEG_QUALITY), 100])

# --- Loop Through Detections ---
for box, cls_id, conf in zip(general_results.boxes.xyxy, general_results.boxes.cls, general_results.boxes.conf):
    class_name = general_class_names.get(int(cls_id), f"Unknown_{int(cls_id)}")
    if class_name not in TARGET_CLASS_MAP:
        print(f"⏭️ Skipping unknown class: {class_name}")
        continue

    print(f"[{object_counter}] Found: {class_name} ({float(conf):.2f})")
    x1, y1, x2, y2 = map(int, box)
    x1 = max(0, x1 - MARGIN)
    y1 = max(0, y1 - MARGIN)
    x2 = min(img.shape[1], x2 + MARGIN)
    y2 = min(img.shape[0], y2 + MARGIN)
    crop = img[y1:y2, x1:x2]

    save_class = TARGET_CLASS_MAP[class_name]
    filename = f"{os.path.splitext(os.path.basename(IMAGE_PATH))[0]}_{class_name}_{object_counter}.jpg"
    out_path = os.path.join(OUTPUT_DIR, save_class, filename)
    crop_and_save(crop, out_path)

    rel_path = out_path.replace("\\", "/")
    coordinates_data[rel_path] = {
        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
        "width": x2 - x1, "height": y2 - y1,
        "confidence": float(conf), "class_name": class_name
    }

    # Detect ports inside Switch or Rack
    if save_class in ['Switch', 'Rack']:
        print(f"🔬 Running port detection inside {class_name}")
        port_results = port_model(crop, conf=CONF_THRESHOLD, verbose=False)[0]

        for port_idx, (port_box, port_conf) in enumerate(zip(port_results.boxes.xyxy, port_results.boxes.conf)):
            px1, py1, px2, py2 = map(int, port_box)
            px1 = max(0, px1 - MARGIN)
            py1 = max(0, py1 - MARGIN)
            px2 = min(crop.shape[1], px2 + MARGIN)
            py2 = min(crop.shape[0], py2 + MARGIN)
            port_crop = crop[py1:py2, px1:px2]

            port_filename = f"{os.path.splitext(os.path.basename(IMAGE_PATH))[0]}_Port_{region_counter}_{port_idx}.jpg"
            port_path = os.path.join(OUTPUT_DIR, "Port", port_filename)
            crop_and_save(port_crop, port_path)

            rel_port_path = port_path.replace("\\", "/")
            coordinates_data[rel_port_path] = {
                "x1": x1 + px1, "y1": y1 + py1,
                "x2": x1 + px2, "y2": y1 + py2,
                "width": px2 - px1, "height": py2 - py1,
                "confidence": float(port_conf),
                "class_name": "Port",
                "parent_region": f"{class_name}_{region_counter}"
            }
        region_counter += 1

    object_counter += 1

# --- Save Coordinates ---
os.makedirs(os.path.dirname(COORDINATES_FILE), exist_ok=True)
with open(COORDINATES_FILE, 'w') as f:
    json.dump(coordinates_data, f, indent=2)

print(f"✅ Done: {IMAGE_PATH}")
print(f"📊 Total components: {object_counter}")
print(f"📍 Coordinates saved in: {COORDINATES_FILE}")
