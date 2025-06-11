import pandas as pd
import os
from PIL import Image
from tqdm import tqdm
import torch
from sentence_transformers import SentenceTransformer
import clip
import faiss
import numpy as np
import difflib
import pickle
 
# Set device
device = "cuda" if torch.cuda.is_available() else "cpu"
 
# Load models
print("🔄 Loading models...")
text_model = SentenceTransformer('all-MiniLM-L6-v2')
clip_model, preprocess = clip.load("ViT-B/32", device=device)
 
# Excel file paths
excel_files = [
    r"EXCELS\Switch\Switch.xlsx",
    r"EXCELS\Rack\Rack.xlsx",
    r"EXCELS\Ports\ports1.xlsx",
    r"EXCELS\Ports\ports2.xlsx",
    r"EXCELS\Cables\Cables.xlsx"
]
 
# Infer category from file name
def get_category_from_path(path):
    fname = os.path.basename(path).lower()
    if "switch" in fname:
        return "Switch"
    elif "rack" in fname:
        return "Rack"
    elif "port" in fname:
        return "Port"
    elif "cable" in fname:
        return "Cable"
    else:
        return "Unknown"
 
# Read Excel files with category info
print("📂 Reading Excel files...")
dfs = []
for path in excel_files:
    df = pd.read_excel(path)
    df["Category"] = get_category_from_path(path)
    dfs.append(df)
 
df = pd.concat(dfs, ignore_index=True)
df = df.dropna(subset=["Name", "Description", "Image"])
df['Image'] = df['Image'].astype(str).str.replace(r'\s+', '', regex=True)
 
# Index all available images from your specific image folders
print("📸 Indexing images in UI/EXCELS folders...")
image_roots = [
    r"EXCELS\Switch\Switch_images",
    r"EXCELS\Rack\Rack_Images",
    r"EXCELS\Ports\ports_1_images",
    r"EXCELS\Ports\ports_2_images",
    r"EXCELS\Cables\Cables_images"
]
 
all_image_files = []
for root in image_roots:
    for dirpath, _, files in os.walk(root):
        for file in files:
            if file.lower().endswith((".png", ".jpg", ".jpeg")):
                all_image_files.append(os.path.join(dirpath, file))
 
# Initialize tracking
missing_images = []
fuzzy_matches = {}
 
# Text embeddings
print("💬 Generating text embeddings...")
def get_text_embedding(row):
    text = f"{row['Name']} {row['Description']}"
    return text_model.encode(text)
 
tqdm.pandas()
df["text_embedding"] = df.progress_apply(get_text_embedding, axis=1)
 
# Image embeddings
print("🖼️ Generating image embeddings...")
def get_image_embedding(image_path):
    try:
        original_path = str(image_path).strip().replace('\n', '')
        filename_key = os.path.basename(original_path).lower().replace(" ", "")
       
        # Build a mapping of normalized filename → full path
        normalized_files = {
            os.path.basename(f).lower().replace(" ", ""): f
            for f in all_image_files
        }
 
        # Fuzzy match against normalized keys
        match = difflib.get_close_matches(filename_key, normalized_files.keys(), n=1, cutoff=0.7)
 
        if match:
            matched_full_path = normalized_files[match[0]]
            fuzzy_matches[image_path] = matched_full_path
        else:
            missing_images.append(image_path)
            raise FileNotFoundError(f"No match for {image_path}")
 
        image = preprocess(Image.open(matched_full_path).convert("RGB")).unsqueeze(0).to(device)
        with torch.no_grad():
            return clip_model.encode_image(image).cpu().numpy()[0]
       
    except Exception as e:
        print(f"⚠️ Error with image {image_path}: {e}")
        return np.zeros(512)
 
df["image_embedding"] = df["Image"].progress_apply(get_image_embedding)
 
# Optional: Save missing and fuzzy matched logs
if missing_images:
    with open("missing_images.txt", "w") as f:
        f.writelines(path + "\n" for path in missing_images)
if fuzzy_matches:
    with open("fuzzy_matched_images.txt", "w", encoding="utf-8") as f:
        for orig, matched in fuzzy_matches.items():
            f.write(f"{orig} --> {matched}\n")
 
# FAISS helper
def create_faiss_index(embeds):
    dim = embeds.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeds)
    return index
 
# Save everything in a single file
# Prepare and save FAISS indexes and embeddings only
print("📦 Saving embeddings and indexes in all_categories_data.pkl...")
all_data = {}
all_metadata = {}
 
for category in df["Category"].unique():
    cat_df = df[df["Category"] == category].copy()
    text_embeds = np.vstack(cat_df["text_embedding"].values)
    image_embeds = np.vstack(cat_df["image_embedding"].values)
 
    text_index = create_faiss_index(text_embeds)
    image_index = create_faiss_index(image_embeds)
 
    all_data[category] = {
        "text_embeddings": text_embeds,
        "image_embeddings": image_embeds,
        "text_index": text_index,
        "image_index": image_index
    }
 
    all_metadata[category] = cat_df.drop(columns=["text_embedding", "image_embedding"])
 
# Save embeddings and indexes
with open("all_categories_data.pkl", "wb") as f:
    pickle.dump(all_data, f)
 
# Save metadata separately
print("🗂️ Saving metadata in metadata.pkl...")
with open("metadata.pkl", "wb") as f:
    pickle.dump(all_metadata, f)
 
print("✅ Done! Saved all_categories_data.pkl and metadata.pkl.")
 
 
 