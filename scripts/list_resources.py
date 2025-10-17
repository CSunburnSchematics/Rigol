import pyvisa

rm = pyvisa.ResourceManager()
resources = rm.list_resources('?*USB*')

print("Available VISA USB connected resources:")
for resource in resources:
    print(resource)
    try:
        instr = rm.open_resource(resource)
        idn = instr.query("*IDN?")
        print(f"  -> Identity: {idn.strip()}")
    except Exception as e:
        print(f"  -> Could not query identity")
    print("\n")
print(len(resources))

# sudo $(which python) list_resources.py