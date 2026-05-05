# Run this script once to build master_daily.csv if you prefer offline
import pandas as pd
import os
from tqdm import tqdm


CLEANED_DIR = r"D:/Downloads/FYP CHINA/data/cleaned_cities"
DAILY_DIR = r"D:/Downloads/FYP CHINA/data/daily_cities"
OUTPUT = r"D:/Downloads/FYP CHINA/data/master_daily.csv"


files = []
for folder in [CLEANED_DIR, DAILY_DIR]:
    if not os.path.exists(folder):
        continue
    for f in os.listdir(folder):
        if f.endswith('.csv'):
            files.append(os.path.join(folder, f))


print('found files:', len(files))


dfs = []
for f in tqdm(files):
    try:
        d = pd.read_csv(f)
        if 'date' in d.columns:
            d['date'] = pd.to_datetime(d['date'], errors='coerce')
        dfs.append(d)
    except Exception as e:
        print('skip', f, e)


if dfs:
    master = pd.concat(dfs, ignore_index=True)
    master = master.drop_duplicates()
    master = master.dropna(subset=['city', 'date'])
    master = master.sort_values(['city','date'])
    master.to_csv(OUTPUT, index=False, encoding='utf-8-sig')
    print('master saved to', OUTPUT)
else:
    print('no data to merge')