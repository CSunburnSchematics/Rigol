import os, glob, subprocess

os.makedirs("CSV", exist_ok=True)

for bin_file in glob.glob("Tests/*.bin"):
    csv_file = os.path.join("CSV", os.path.basename(bin_file).replace(".bin", ".csv"))
    print(f"Converting: {bin_file} -> {csv_file}")
    subprocess.run(["python", "binary_to_csv.py", bin_file, csv_file])

print("All conversions complete!")
