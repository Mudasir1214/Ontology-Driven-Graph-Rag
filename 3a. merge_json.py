import json
import os
import glob

# ================= Configuration Section =================
# Your JSON folder path (note the r prefix means raw string, so no need to worry about backslash escaping)
INPUT_FOLDER = r"./input_data/batch_data/"

# Output file save path (recommended to save outside the folder or use a different name)
OUTPUT_DIR = r"./output_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_FILE = f"./{OUTPUT_DIR}/combined_knowledge_base.json"


# ===========================================

def merge_json_files():
    print(f"📂 Scanning folder: {INPUT_FOLDER} ...")
    
    # 1. Get all .json files
    json_files = glob.glob(os.path.join(INPUT_FOLDER, "*.json"))
    
    if not json_files:
        print("❌ Error: No .json files found in this folder!")
        return

    print(f"✅ Found {len(json_files)} JSON files. Starting merge...")

    combined_entries = []

    # 2. Iterate and read each file
    for file_path in json_files:
        filename = os.path.basename(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # --- Smart merge logic ---
                # Case A: If file itself is a list [{}, {}] -> directly extend
                if isinstance(data, list):
                    combined_entries.extend(data)
                    
                # Case B: If file is a dict and contains 'entries' key -> extract entries and extend
                elif isinstance(data, dict) and "entries" in data:
                     if isinstance(data["entries"], list):
                         combined_entries.extend(data["entries"])
                     else:
                         combined_entries.append(data["entries"]) # if entries is a single object
                
                # Case C: If file is a single dict object {} -> append as one entry
                elif isinstance(data, dict):
                    combined_entries.append(data)
                
                print(f"  -> Merged: {filename}")

        except Exception as e:
            print(f"⚠️ Skipping file {filename}: read error - {e}")

    # 3. Construct final structure
    # To keep consistent with your previous format, wrap it inside "entries"
    final_structure = {
        "entries": combined_entries
    }

    # 4. Write to new file
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_structure, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*40)
        print(f"🎉 Merge completed!")
        print(f"📊 Total number of entries: {len(combined_entries)}")
        print(f"💾 File saved as: {OUTPUT_FILE}")
        print("="*40)
        
    except Exception as e:
        print(f"❌ Failed to write file: {e}")

if __name__ == "__main__":
    merge_json_files()