#!/usr/bin/env python3
"""
Synchronizes the root .version file across the repository.
Updates package.json and backend/main.py (if needed).
"""
import json
import os
import sys

def main():
   root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
   version_file = os.path.join(root_dir, ".version")
   
   if not os.path.exists(version_file):
       print("Error: .version file not found")
       sys.exit(1)
       
   with open(version_file, "r") as f:
       version = f.read().strip()
       
   print(f"Syncing version {version} across repository...")
   
   # 1. Update package.json
   pkg_file = os.path.join(root_dir, "package.json")
   if os.path.exists(pkg_file):
       with open(pkg_file, "r") as f:
           pkg_data = json.load(f)
       pkg_data["version"] = version.split("-")[0]  # npm requires semantic versioning
       with open(pkg_file, "w") as f:
           json.dump(pkg_data, f, indent=2)
           f.write("\n")
       print("✅ Updated package.json")
       
   print("Sync complete.")

if __name__ == "__main__":
   main()
