import pandas as pd
import os


OUTPUT_DIR = r"./output_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# 1. Set file paths (please ensure the paths are correct)
input_file_path = f"{OUTPUT_DIR}/Benchmark_Final_600.xlsx"
output_file_path = f"{OUTPUT_DIR}/Graph_RAG_Correct_Only.xlsx"

def extract_correct_rows():
    print(f"Reading file: {input_file_path} ...")
    
    try:
        # Read Excel file
        df = pd.read_excel(input_file_path)
        
        # Check if target column exists
        if 'Graph_RAG_Res' not in df.columns:
            print("❌ Error: Column 'Graph_RAG_Res' not found")
            return

        # 2. Filtering logic: rows containing "Correct" (including "Correct" and "Correct (Refusal)")
        # na=False prevents errors from NaN values
        filtered_df = df[df['Graph_RAG_Res'].astype(str).str.contains("Correct", na=False)].copy()
        
        count = len(filtered_df)
        print(f"✅ Filtering completed. Found {count} correct answers.")
        
        if count == 0:
            print("No matching data found. File will not be saved.")
            return

        # 3. Reindex from the beginning
        # Reset index, drop=True means discard the old index
        filtered_df.reset_index(drop=True, inplace=True)
        
        # If needed, explicitly add a "No." column as new index (1, 2, 3...)
        # insert(position, column_name, data)
        filtered_df.insert(0, 'New_ID', range(1, count + 1))

        # 4. Save to new file
        filtered_df.to_excel(output_file_path, index=False)
        print(f"🎉 File saved to: {output_file_path}")

    except FileNotFoundError:
        print(f"❌ Error: File not found. Please check the path: {input_file_path}")
    except Exception as e:
        print(f"❌ Unknown error occurred: {e}")

if __name__ == "__main__":
    extract_correct_rows()