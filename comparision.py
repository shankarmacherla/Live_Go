import numpy as np

import pandas as pd

import faiss

import pickle

import os

import sys

import json
 
# --- Input Args ---

if len(sys.argv) != 6:

    print(

        "Usage: python comparison.py <catalog_path> <cropped_path> <metadata_path> <csv_output_path> <html_output_path>"

    )

    sys.exit(1)
 
catalog_path = sys.argv[1]

cropped_path = sys.argv[2]

metadata_path = sys.argv[3]

csv_output_path = sys.argv[4]

html_output_path = sys.argv[5]
 
top_k = 1 # get top 3 matches for better debugging
 
# --- Load Data ---

print("[INFO] Loading catalog, cropped embeddings, and metadata...")
 
with open(catalog_path, "rb") as f:

    catalog_data = pickle.load(f)
 
with open(cropped_path, "rb") as f:

    cropped_data = pickle.load(f)
 
metadata = pd.read_pickle(metadata_path)
 
# --- Load Coordinates Data ---

coordinates_data = {}

coordinates_file = "static/segmented_outputs/coordinates.json"

if os.path.exists(coordinates_file):

    with open(coordinates_file, 'r') as f:

        coordinates_data = json.load(f)

    print(f"[INFO] Loaded coordinates for {len(coordinates_data)} components")

else:

    print("[WARNING] No coordinates file found - coordinates will be empty")
 
 
# --- Normalize for cosine similarity ---

def l2_normalize(x):

    return x / np.linalg.norm(x, axis=1, keepdims=True)
 
 
# --- Results Container ---

results = []
 
# Helper function to get coordinates for an image

def get_coordinates_for_image(cropped_img_path):

    coords = {}

    # Try exact path first

    if cropped_img_path in coordinates_data:

        coords = coordinates_data[cropped_img_path]

    else:

        # Try without leading slash

        path_without_slash = cropped_img_path.lstrip('/')

        if path_without_slash in coordinates_data:

            coords = coordinates_data[path_without_slash]

        else:

            # Try with leading slash

            path_with_slash = '/' + cropped_img_path.lstrip('/')

            if path_with_slash in coordinates_data:

                coords = coordinates_data[path_with_slash]

            else:

                # Try filename matching as last resort

                filename = os.path.basename(cropped_img_path)

                for key in coordinates_data.keys():

                    if os.path.basename(key) == filename:

                        coords = coordinates_data[key]

                        break

    return coords
 
# Helper function to clean up cropped image path

def clean_cropped_path(cropped_img_path):

    if 'segmented_outputs' in cropped_img_path:

        parts = cropped_img_path.split('segmented_outputs')

        if len(parts) > 1:

            cropped_img_path = '/static/segmented_outputs' + parts[1].replace('\\', '/')

        else:

            cropped_img_path = cropped_img_path.replace('\\', '/')

            if ':' in cropped_img_path:

                cropped_img_path = '/' + '/'.join(cropped_img_path.split('/')[-3:])

    return cropped_img_path
 
# --- First, collect ALL cropped images ---

all_cropped_images = []

all_categories = set(cropped_data.keys())

print(f"[INFO] Found categories with cropped images: {sorted(all_categories)}")
 
for category in sorted(all_categories):

    crop_paths = cropped_data[category]["image_paths"]

    for path in crop_paths:

        cleaned_path = clean_cropped_path(path)

        all_cropped_images.append({

            'path': cleaned_path,

            'category': category,

            'original_path': path

        })
 
print(f"[INFO] Total cropped images found: {len(all_cropped_images)}")
 
# --- Process each cropped image ---

for img_info in all_cropped_images:

    cropped_img_path = img_info['path']

    category = img_info['category']

    # Get coordinates for this image

    coords = get_coordinates_for_image(cropped_img_path)

    # Check if we have catalog data for this category

    if category in catalog_data and category in metadata:

        # Try to find a match

        crop_embeds = cropped_data[category]["image_embeddings"]

        crop_paths = cropped_data[category]["image_paths"]

        cat_embeds = catalog_data[category]["image_embeddings"]

        # Find the index of this specific image

        img_index = None

        for i, path in enumerate(crop_paths):

            if clean_cropped_path(path) == cropped_img_path:

                img_index = i

                break

        if img_index is not None and len(cat_embeds) > 0:

            # Get embedding for this specific image

            crop_embed = l2_normalize(np.array([crop_embeds[img_index]]))

            cat_embeds_norm = l2_normalize(np.array(cat_embeds))

            # Find best match

            dim = cat_embeds_norm.shape[1]

            index = faiss.IndexFlatIP(dim)

            index.add(cat_embeds_norm)

            distances, indices = index.search(crop_embed, 1)

            if len(indices[0]) > 0:

                best_idx = indices[0][0]

                best_score = float(distances[0][0])

                meta_row = metadata[category].iloc[best_idx]

                # Clean catalog image path

                matched_img = meta_row['Image']

                if isinstance(matched_img, str) and 'static' in matched_img:

                    matched_img = '/' + matched_img.split('static', 1)[1].replace('\\', '/')

                result_data = {

                    'cropped_image': cropped_img_path,

                    'category': category,

                    'name': meta_row['Name'],

                    'description': meta_row['Description'],

                    'matched_image': matched_img,

                    'image_path': cropped_img_path,

                    'similarity_score': best_score

                }

                print(f"[INFO] Found match for {os.path.basename(cropped_img_path)} → {meta_row['Name']} (Score: {best_score:.4f})")

            else:

                # No match found, but still include the image

                result_data = {

                    'cropped_image': cropped_img_path,

                    'category': category,

                    'name': 'No match found',

                    'description': 'This component was detected but no matching catalog entry was found',

                    'matched_image': '',

                    'image_path': cropped_img_path,

                    'similarity_score': 0.0

                }

                print(f"[INFO] No match found for {os.path.basename(cropped_img_path)}")

        else:

            # No embeddings available, but still include the image

            result_data = {

                'cropped_image': cropped_img_path,

                'category': category,

                'name': 'No match found',

                'description': 'This component was detected but no matching catalog entry was found',

                'matched_image': '',

                'image_path': cropped_img_path,

                'similarity_score': 0.0

            }

            print(f"[INFO] No embeddings available for {os.path.basename(cropped_img_path)}")

    else:

        # No catalog data for this category, but still include the image

        result_data = {

            'cropped_image': cropped_img_path,

            'category': category,

            'name': 'No catalog available',

            'description': f'This {category} component was detected but no catalog exists for this category',

            'matched_image': '',

            'image_path': cropped_img_path,

            'similarity_score': 0.0

        }

        print(f"[INFO] No catalog data for {category}: {os.path.basename(cropped_img_path)}")

    # Add coordinate information

    if coords:

        x1, y1, x2, y2 = coords.get('x1', 0), coords.get('y1', 0), coords.get('x2', 0), coords.get('y2', 0)

        width, height = coords.get('width', 0), coords.get('height', 0)

        confidence = coords.get('confidence', 0)

        coordinates_text = f"Position: ({x1},{y1}) to ({x2},{y2})\nSize: {width}×{height} pixels\nConfidence: {confidence:.2f}"

        result_data['coordinates'] = coordinates_text

    else:

        result_data['coordinates'] = 'Coordinates not available'

    results.append(result_data)
 
# --- Assemble DataFrame ---

df = pd.DataFrame(results)
 
# Keep all results including duplicates - every cropped image should appear in CSV

# This ensures complete visibility of all detected components

print(f"[INFO] Total results in CSV: {len(df)} cropped images")
 
 
# --- Helper to render images in HTML ---

def path_to_img_html(path):

    return f'<img src="{path}" width="100" onerror="this.onerror=null; this.src=\'/static/images/image-not-found.svg\'; this.alt=\'Image not found\'"/>'
 
 
df['Cropped Image'] = df['cropped_image'].apply(path_to_img_html)

df['Matched Catalog Image'] = df['matched_image'].apply(path_to_img_html)
 
# --- Save Outputs ---

df.to_csv(csv_output_path, index=False)
 
df_display = df[[

    'cropped_image', 'category', 'name', 'description', 'matched_image',

    'image_path', 'similarity_score', 'coordinates'

]]
 
df_display.to_html(html_output_path, escape=False, index=False)
 
print(f"\n✅ Matching complete. Results saved to:")

print(f"    → CSV : {csv_output_path}")

print(f"    → HTML: {html_output_path}")

 