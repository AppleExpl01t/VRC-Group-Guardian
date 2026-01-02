import sys
import sysconfig
import os
import shutil

print(f"Python executable: {sys.executable}")
print(f"Scripts: {sysconfig.get_path('scripts')}")

flet_path = shutil.which("flet")
if flet_path:
    print(f"Flet found at: {flet_path}")
else:
    scripts_dir = sysconfig.get_path('scripts')
    potential_flet = os.path.join(scripts_dir, "flet.exe")
    if os.path.exists(potential_flet):
         print(f"Flet found in scripts: {potential_flet}")
    else:
         print("Flet not found in scripts")
