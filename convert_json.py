import pandas as pd
import json

# Input CSV path
csv_path = "matched_catalog_results_top1.csv"
# Output JSON path
json_path = "matched_catalog_results_top1.json"

# Load CSV
df = pd.read_csv(csv_path)

# Group by cropped_label and build matches
result = []
for label, group in df.groupby("cropped_label"):
    matches = []
    for _, row in group.iterrows():
        matches.append({
            "match_name": row["match_name"],
            "match_description": row["match_description"],
            "match_image": row["match_image"],
            "score": float(row["score"])
        })
    
    result.append({
        "cropped_label": label,
        "matches": matches
    })

# Save to JSON
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=4)

print(f"✅ Converted '{csv_path}' to '{json_path}'")
