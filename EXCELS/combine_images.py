import os
import re
import pandas as pd
from openpyxl import load_workbook

# === CONFIGURATION ===
excel_path = "Cables/Cables_Original.xlsx"  # Your single Excel file
image_folder = "Cables/Cables_images"      # Flat folder with all extracted images
output_path = "Cables/Cables.xlsx"  # Where to save updated file

# === Helper to sanitize name (convert to filename) ===
def sanitize_filename(name):
    if name is None:
        return "Unnamed"
    name = str(name).strip()
    name = name.replace(" ", "_")
    name = re.sub(r'[\\/*?:"<>|\n\r\t]', '', name)
    return name

# === Load Excel and replace Image column ===
df = pd.read_excel(excel_path)

for idx, row in df.iterrows():
    name = row.get("Name", "")
    sanitized = sanitize_filename(name)
    expected_image = os.path.join(image_folder, f"{sanitized}.jpg")

    # Fallback match if exact name not found
    if not os.path.exists(expected_image):
        matches = [f for f in os.listdir(image_folder) if f.startswith(sanitized)]
        if matches:
            expected_image = os.path.join(image_folder, matches[0])
        else:
            expected_image = "Image not found"

    df.at[idx, "Image"] = expected_image

# === Save updated Excel ===
df.to_excel(output_path, index=False)
print(f"✅ Saved updated Excel: {output_path}")
