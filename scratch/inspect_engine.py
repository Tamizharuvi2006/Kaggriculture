with open(r'C:\Users\aruvi\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\site-packages\kaggle_environments\envs\kaggriculture\kaggriculture.py') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'def _daily_refresh_plants' in line:
        print(''.join(lines[i:i+40]))
        break
