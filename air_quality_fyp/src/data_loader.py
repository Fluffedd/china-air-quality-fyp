import pandas as pd
import os
from .config import CLEANED_DIR, DAILY_DIR, MASTER_DAILY


# Load single master, if not exists create by merging


def create_master_if_missing(force=False):
    if os.path.exists(MASTER_DAILY) and not force:
        return pd.read_csv(MASTER_DAILY, parse_dates=["date"])


    files = []
    for folder in [CLEANED_DIR, DAILY_DIR]:
        if not os.path.exists(folder):
            continue
        for f in os.listdir(folder):
            if f.endswith(".csv"):
                files.append(os.path.join(folder, f))


    if not files:
        return pd.DataFrame()


    dfs = []
    for f in files:
        try:
            d = pd.read_csv(f)
            if "date" in d.columns:
                d["date"] = pd.to_datetime(d["date"], errors="coerce")
            dfs.append(d)
        except Exception as e:
            print("skip", f, e)


    master = pd.concat(dfs, ignore_index=True)
    master = master.drop_duplicates()
    master = master.dropna(subset=["city", "date"], how="any")
    master = master.sort_values(["city", "date"])
    master.to_csv(MASTER_DAILY, index=False, encoding="utf-8-sig")
    return master




def load_master(force=False):
    return create_master_if_missing(force=force)