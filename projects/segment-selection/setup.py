import os

def create_directory_structure(base_path):
    # Define the directory paths relative to the base path
    directory_paths = [
        os.path.join(base_path, 'data'),
        os.path.join(base_path, 'data/raw'),
        os.path.join(base_path, 'data/served'),
        os.path.join(base_path, 'data/controlled')
    ]

    for folder_path in directory_paths:
        # Check if the directory already exists
        if not os.path.exists(folder_path):
            # If it doesn't exist, create it
            os.makedirs(folder_path)
            print(f"Directory '{folder_path}' was created.")
        else:
            # If it exists, print a message
            print(f"Directory '{folder_path}' already exists.")

def main():
    # Define the base path
    base_path = os.path.join('projects', 'segments')
    create_directory_structure(base_path)

if __name__ == "__main__":
    main()
