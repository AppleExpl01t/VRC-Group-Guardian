import zipfile
import os
import shutil

def list_files(startpath):
    for root, dirs, files in os.walk(startpath):
        for file in files:
            yield os.path.join(root, file)

def create_robust_app_zip():
    app_zip_path = r'build/flutter/app/app.zip'
    src_dir = r'src'
    site_packages_dir = r'build/site-packages'
    
    # Ensure build/flutter/app exists
    os.makedirs(os.path.dirname(app_zip_path), exist_ok=True)
    
    print(f"Creating fresh {app_zip_path}...")
    
    with zipfile.ZipFile(app_zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        # 1. Add Source Files
        print(f"Adding source files from {src_dir}...")
        for file_path in list_files(src_dir):
            rel_path = os.path.relpath(file_path, src_dir)
            arcname = rel_path.replace(os.sep, '/') # Force forward slashes
            
            # Skip python cache
            if '__pycache__' in arcname or arcname.endswith('.pyc'):
                continue
                
            print(f"  Adding src: {arcname}")
            z.write(file_path, arcname)
            
        # 2. Add Site Packages
        print(f"Adding site packages from {site_packages_dir}...")
        if os.path.exists(site_packages_dir):
            for file_path in list_files(site_packages_dir):
                rel_path = os.path.relpath(file_path, site_packages_dir)
                arcname = rel_path.replace(os.sep, '/') # Force forward slashes
                
                # Skip python cache and dist-info (optional, but saves space)
                if '__pycache__' in arcname or arcname.endswith('.pyc'):
                    continue
                # if '.dist-info' in arcname: continue # Maybe keep for metadata? Better keep it.
                
                # Check for collision
                # If src and site-packages have same file, src wins (already added)
                # But zipfile allows duplicates. We should check.
                if arcname in z.namelist():
                    print(f"  Skipping collision: {arcname}")
                    continue
                    
                # print(f"  Adding lib: {arcname}") # Verbose
                z.write(file_path, arcname)
        else:
            print(f"Warning: {site_packages_dir} does not exist!")

    print("Success! app.zip created.")
    
    # Verify critical files
    with zipfile.ZipFile(app_zip_path, 'r') as z:
        names = z.namelist()
        print(f"Total files: {len(names)}")
        if 'main.py' in names: print("  YES: main.py")
        else: print("  NO: main.py MISSING")
        
        if 'certifi/__init__.py' in names: print("  YES: certifi")
        else: print("  NO: certifi MISSING")
        
        if 'httpx/__init__.py' in names: print("  YES: httpx")
        else: print("  NO: httpx MISSING")
        
        # Check backslashes
        has_backslash = any('\\' in n for n in names)
        print(f"  Backslashes detected: {has_backslash}")

if __name__ == "__main__":
    create_robust_app_zip()
