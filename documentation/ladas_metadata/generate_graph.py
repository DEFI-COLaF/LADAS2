import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import glob
import re
from collections import defaultdict, Counter
import requests

import xml.etree.ElementTree as ET
import time

sns.set_theme(rc={'figure.figsize':(11.7,8.27)})

metadata = pd.read_csv("./metadata.csv", index_col=0)
metadata_monographie = pd.read_csv("./data_mono.csv", header=None, names=["type", "ark", "titre", "date", "auteur", "langue"], sep=";", usecols=range(6))

datacat = pd.read_csv("./catalogs_subset_stats (1).csv", names=["ark", "filename", "year", "folio"])

datacat.filename = datacat.filename.apply(lambda x: (re.findall("(12148_[a-z0-9]+)_", x) or [x])[0])
subsets = defaultdict(list)

re_bpt = re.compile(r"((?:bpt6|bd6t|cb)[a-z0-9]+)_")
re_persee = re.compile(r"^[^_]+_[^_]+_(\d{4})_(?:[a-z]{3})_")


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}

def fetch_gallica_date(ark_id, max_retries=4, base_delay=2):
    url = f"https://gallica.bnf.fr/services/OAIRecord?ark={ark_id}"

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()

            root = ET.fromstring(response.content)

            ns = {
                "dc": "http://purl.org/dc/elements/1.1/",
                "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/"
            }

            date_elem = root.find(".//dc:date", ns)
            return date_elem.text if date_elem is not None else None

        except requests.RequestException as e:
            print(f"Attempt {attempt+1} failed: {e}")

            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"Waiting {delay:.2f}s...")
            time.sleep(delay)

    return None

def clean_subset_name(subset):
    subset_clean = subset.replace("-test", "").replace("-train", "").replace("-valid", "")
    return {
        "administrative-report": "Admin",
        "romans-19": "Romans19",
        "picard": "Others",
        "typewriter": "Others",
        "magazine-tech": "Tech. Magazines",
        "persee": "Persée",
        "these": "These",
        "catalogue": "Catalogue",
        "theatre": "Theatre",
        "monographies": "Monographs"
    }.get(subset_clean, "Others")


def extract_ark(filename):
    match = re_bpt.findall(filename)
    return match[0] if match else None


def get_catalogue_date(filename, ark):
    # 1. datacat
    line_metadata_cat = datacat[datacat["filename"] == filename]
    if not line_metadata_cat.empty:
        return line_metadata_cat['year'].iloc[0]

    # 2. metadata_monographie
    if ark:
        line = metadata_monographie[metadata_monographie["ark"] == ark]

        if not line.empty and not pd.isna(line['date'].iloc[0]):
            return line['date'].iloc[0]

        # 3. fallback API
        if ark.startswith("bpt6k"):
            return fetch_gallica_date(ark)

    return None


def get_general_date(filename, subset, ark):
    # 1. metadata index
    try:
        return metadata.loc[filename]['year']
    except KeyError:
        pass

    # 2. filename heuristics
    if "dictionnaire" in filename:
        m = re.search(r'^([0-9]{2})_', filename)
        return m.group(1) if m else None

    if "persee" in subset:
        m = re_persee.findall(filename)
        return m[0] if m else None

    if "monographies" in subset or "roman" in subset:
        m = re.search(r'^([0-9]{4})_', filename)
        return m.group(1) if m else None

    if "these" in subset:
        m = re.search(r'^[0-9]{4}', filename)
        return m.group(0) if m else None

    if "theatre" in subset or "magazine" in subset or "admin" in subset:
        m = re.search(r'_([0-9]{4})_', filename)
        if m:
            return m.group(1)

        if ark:
            line = metadata_monographie[metadata_monographie["ark"] == ark]
            if not line.empty:
                return line['date'].iloc[0]

    if "fingers" in subset:
        return 2000

    return None


# ---------------- MAIN LOOP ---------------- #

n_missing = 0

for file in glob.glob("../LADAS2-REVIEW/*/*/*.jpg"):
    _, _, split, subset, filename = file.split("/")
    simpler_subset = clean_subset_name(subset)

    ark = extract_ark(filename)
    date = None

    if "catalogue" in subset:
        date = get_catalogue_date(filename, ark)
    else:
        date = get_general_date(filename, subset, ark)

    if date is None:
        print("Missing:", filename)
        n_missing += 1

    subsets[subset].append((filename, date, simpler_subset))

print("Total missing:", n_missing)