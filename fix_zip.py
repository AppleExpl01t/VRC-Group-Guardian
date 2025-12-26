import zipfile
import os

def pack_deps():
    zip_path = r'build/flutter/app/app.zip'
    pkg_dir = r'build/temp_pkg'
    
    if not os.path.exists(zip_path):
        print(f"Error: {zip_path} not found.")
        return
    if not os.path.exists(pkg_dir):
        print(f"Error: {pkg_dir} not found.")
        return

    print(f"Opening {zip_path}...")
    try:
        with zipfile.ZipFile(zip_path, 'a') as z:
            existing_files = set(z.namelist())
            count = 0
            for root, dirs, files in os.walk(pkg_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, pkg_dir)
                    arcname = rel_path.replace(os.sep, '/')
                    
                    if arcname not in existing_files:
                        z.write(full_path, arcname)
                        count += 1
            print(f"Added {count} files to {zip_path}")
            
        # Verify
        with zipfile.ZipFile(zip_path, 'r') as z:
            if 'certifi/core.py' in z.namelist() or 'certifi/__init__.py' in z.namelist():
                print("Verification: certifi found in zip.")
            else:
                print("Verification: certifi NOT found in zip (might be packaged differently).")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    pack_deps()
