import os
import glob
import numpy as np
from PIL import Image
from tqdm import tqdm
import torch
import clip
import faiss
import pickle

# Set device
device = "cuda" if torch.cuda.is_available() else "cpu"

# Load CLIP model
print("[INFO] Loading CLIP model...")
model, preprocess = clip.load("ViT-B/32", device=device)

# Generate CLIP embedding from image path
def generate_clip_embedding(img_path):
    try:
        image = preprocess(Image.open(img_path).convert("RGB")).unsqueeze(0).to(device)
        with torch.no_grad():
            image_features = model.encode_image(image)
        return image_features.cpu().numpy()[0]
    except Exception as e:
        print(f"[ERROR] Failed to process {img_path}: {e}")
        return np.zeros(512)

# Build FAISS index
def create_faiss_index(embeds):
    dim = embeds.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeds)
    return index

# Main embedding generator
def generate_category_embeddings(base_dir):
    category_data = {}
    categories = [name for name in os.listdir(base_dir)
                  if os.path.isdir(os.path.join(base_dir, name))]

    for category in categories:
        print(f"[INFO] Processing category: {category}")
        cat_dir = os.path.join(base_dir, category)
        # Look for both jpg and png files
        jpg_paths = glob.glob(os.path.join(cat_dir, "*.jpg"))
        png_paths = glob.glob(os.path.join(cat_dir, "*.png"))
        image_paths = jpg_paths + png_paths
        
        # Debug info
        print(f"[INFO] Found {len(image_paths)} images in {cat_dir}")
        embeddings = []

        for img_path in tqdm(image_paths, desc=f"[{category}]"):
            emb = generate_clip_embedding(img_path)
            embeddings.append(emb)

        if len(embeddings) == 0:
            print(f"[WARN] No images found for category: {category}")
            continue

        embeddings = np.array(embeddings).astype("float32")
        index = create_faiss_index(embeddings)

        category_data[category] = {
            "image_embeddings": embeddings,
            "image_index": index,
            "image_paths": image_paths
        }

    return category_data

# Run and save
if __name__ == "__main__":
    import sys
    
    # Use command line arguments if provided, otherwise use defaults
    if len(sys.argv) >= 3:
        segmented_dir = sys.argv[1]
        output_file = sys.argv[2]
    else:
        segmented_dir = "static/segmented_outputs"
        output_file = "cropped_clip_data.pkl"
        
    print(f"[INFO] Processing segmented directory: {segmented_dir}")
    print(f"[INFO] Output will be saved to: {output_file}")
    
    # Clean any existing output file to avoid duplicate entries
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"[INFO] Removed existing output file: {output_file}")

    print("[INFO] Generating cropped embeddings...")
    cropped_data = generate_category_embeddings(segmented_dir)

    with open(output_file, "wb") as f:
        pickle.dump(cropped_data, f)

    print(f"[✅] Saved cropped embeddings to {output_file}")