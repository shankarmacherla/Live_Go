import os
import pandas as pd

# === CONFIGURATION ===
excel_folder = "Switch/Switch"  # Folder with all Excel files
output_path = "Switch/Switch.xlsx"

# === Initialize empty list to hold dataframes ===
all_dfs = []

# === Loop through all Excel files ===
for file in os.listdir(excel_folder):
    if file.endswith(".xlsx"):
        file_path = os.path.join(excel_folder, file)
        print(f"📄 Reading: {file}")
        df = pd.read_excel(file_path)
        df['Source_File'] = file  # Optional: Add filename column for traceability
        all_dfs.append(df)

# === Concatenate all DataFrames ===
combined_df = pd.concat(all_dfs, ignore_index=True)

# === Save to one Excel file ===
combined_df.to_excel(output_path, index=False)
print(f"✅ Combined Excel saved to: {output_path}")
