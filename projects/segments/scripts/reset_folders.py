import os

def reset_folders():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the segments directory
    segments_dir = os.path.dirname(script_dir)
    
    # Define paths for the folders relative to the segments directory
    folders = [
        os.path.join(segments_dir, 'data', 'controlled'),
        os.path.join(segments_dir, 'data', 'raw'),
        os.path.join(segments_dir, 'data', 'served')
    ]

    # Loop through each folder and delete .csv files
    for folder in folders:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                if filename.endswith('.csv'):
                    file_path = os.path.join(folder, filename)
                    try:
                        os.remove(file_path)
                        print(f"Deleted: {file_path}")
                    except Exception as e:
                        print(f"Error deleting {file_path}: {e}")
        else:
            print(f"Warning: Directory {folder} does not exist")
                
    # Check if the files are deleted
    deleted_files = {}
    for folder in folders:
        if os.path.exists(folder):
            deleted_files[folder] = os.listdir(folder)
        else:
            deleted_files[folder] = []
    
    print("Remaining files in directories:")
    for folder, files in deleted_files.items():
        print(f"{folder}: {len(files)} files")
    
    return deleted_files


def main():    
    reset_folders()
    
if __name__ == "__main__":
    main()