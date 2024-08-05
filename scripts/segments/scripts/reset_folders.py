import  os

def reset_folders():
    # Define paths for the folders
    folders = ['data/controlled', 'data/raw', 'data/served']

    # Loop through each folder and delete .csv files
    for folder in folders:
        for filename in os.listdir(folder):
            if filename.endswith('.csv'):
                os.remove(os.path.join(folder, filename))
                
    # Check if the files are deleted
    deleted_files = {folder: os.listdir(folder) for folder in folders}
    deleted_files


def main():    
    reset_folders()
    
if __name__ == "__main__":
    main()