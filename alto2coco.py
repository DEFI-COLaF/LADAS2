"""
alto4_to_coco.py — Convert ALTO4 (eScriptorium/kraken) XML to COCO JSON
------------------------------------------------------------------------
Modelled on voc2coco.py. Labels are discovered automatically from the
<Tags> section of the XMLs — no labels.txt needed.
Output is written as coco.json inside the provided directory.

Usage:
    python alto4_to_coco.py data/dataset-dfine/alto

Output:
    data/dataset-dfine/alto/coco.json
"""

import os
import glob
import json
import argparse
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from tqdm import tqdm


ALTO_NS = "http://www.loc.gov/standards/alto/ns-v4#"


def collect_labels(ann_paths: List[str]) -> Dict[str, int]:
    """
    Scan all XMLs and build label2id from every block-type OtherTag (ID=BT*).
    Line tags (ID=LT*) are excluded.
    IDs assigned alphabetically for stability.
    """
    labels = set()

    for path in ann_paths:
        root = ET.parse(path).getroot()

        for tag in root.findall(f".//{{{ALTO_NS}}}OtherTag"):
            tid = tag.get("ID", "")
            label = tag.get("LABEL")

            if label and tid.startswith("BT"):
                labels.add(label)

    return {
        label: idx
        for idx, label in enumerate(sorted(labels), start=1)
    }


def parse_tag_map(annotation_root) -> Dict[str, str]:
    """
    Build {tag_id: label} from <Tags><OtherTag ID=... LABEL=...>.
    """
    tag_map = {}

    for tag in annotation_root.findall(f".//{{{ALTO_NS}}}OtherTag"):
        tid = tag.get("ID")
        label = tag.get("LABEL")

        if tid and label:
            tag_map[tid] = label

    return tag_map


def get_image_info(annotation_root) -> dict:
    """
    Extract filename and page dimensions from ALTO4.
    """

    filename_el = annotation_root.find(f".//{{{ALTO_NS}}}fileName")

    filename = (
        filename_el.text.strip()
        if filename_el is not None
        else "unknown.jpg"
    )

    img_name = os.path.basename(filename)

    page = annotation_root.find(f".//{{{ALTO_NS}}}Page")

    width = int(float(page.get("WIDTH", 0)))
    height = int(float(page.get("HEIGHT", 0)))

    return {
        "file_name": img_name,
        "height": height,
        "width": width,
    }


def get_coco_annotation_from_block(
    block,
    tag_map: Dict[str, str],
    label2id: Dict[str, int]
) -> Optional[dict]:
    """
    Convert one <TextBlock> to a COCO annotation dict.

    Returns None if:
    - unknown label
    - invalid geometry
    - malformed polygon
    """

    tagrefs = block.get("TAGREFS", "")

    label = None

    for ref in tagrefs.split():
        if ref in tag_map:
            label = tag_map[ref]
            break

    if label is None or label not in label2id:
        return None

    category_id = label2id[label]

    # Prefer rectangular geometry
    hpos = block.get("HPOS")
    vpos = block.get("VPOS")
    w_attr = block.get("WIDTH")
    h_attr = block.get("HEIGHT")

    if None not in (hpos, vpos, w_attr, h_attr):

        xmin = float(hpos)
        ymin = float(vpos)
        o_width = float(w_attr)
        o_height = float(h_attr)

    else:
        # Fallback to polygon
        poly = block.find(f".//{{{ALTO_NS}}}Polygon")

        if poly is None:
            return None

        try:
            pts = [
                float(v)
                for v in poly.get("POINTS", "")
                .replace(",", " ")
                .split()
            ]
        except ValueError:
            return None

        # Need x,y pairs
        if len(pts) < 4 or len(pts) % 2 != 0:
            return None

        xs = pts[0::2]
        ys = pts[1::2]

        xmin = min(xs)
        xmax = max(xs)

        ymin = min(ys)
        ymax = max(ys)

        o_width = xmax - xmin
        o_height = ymax - ymin

    # Skip invalid boxes
    if o_width <= 0 or o_height <= 0:

        print(
            f"[WARN] Invalid bbox skipped: "
            f"({xmin}, {ymin}, {o_width}, {o_height})"
        )

        return None

    return {
        "area": o_width * o_height,
        "iscrowd": 0,
        "bbox": [xmin, ymin, o_width, o_height],
        "category_id": category_id,
        "ignore": 0,
        "segmentation": [],
    }


def convert_altos_to_cocojson(
    annotation_paths: List[str],
    label2id: Dict[str, int],
    output_jsonpath: str
):

    output_json_dict = {
        "images": [],
        "type": "instances",
        "annotations": [],
        "categories": [],
    }

    bnd_id = 1

    print("Start converting!")

    for a_path in tqdm(annotation_paths):

        ann_tree = ET.parse(a_path)
        ann_root = ann_tree.getroot()

        tag_map = parse_tag_map(ann_root)

        img_info = get_image_info(ann_root)

        # Integer image IDs for COCOeval compatibility
        img_id = len(output_json_dict["images"]) + 1
        img_info["id"] = img_id

        output_json_dict["images"].append(img_info)

        for block in ann_root.findall(f".//{{{ALTO_NS}}}TextBlock"):

            ann = get_coco_annotation_from_block(
                block,
                tag_map,
                label2id
            )

            if ann is None:
                continue

            ann.update({
                "image_id": img_id,
                "id": bnd_id
            })

            output_json_dict["annotations"].append(ann)

            bnd_id += 1

    for label, label_id in label2id.items():

        output_json_dict["categories"].append({
            "supercategory": label.split("-")[0],
            "id": label_id,
            "name": label,
        })

    with open(output_jsonpath, "w", encoding="utf-8") as f:
        json.dump(output_json_dict, f, indent=2)

    print(
        f"Saved "
        f"{len(output_json_dict['images'])} images, "
        f"{len(output_json_dict['annotations'])} annotations, "
        f"{len(output_json_dict['categories'])} categories "
        f"-> {output_jsonpath}"
    )


def check_labels(label2id: Dict[str, int], labels_txt: str):
    """
    Compare current split labels against a shared reference labels.txt.

    - First run: creates labels.txt
    - Later runs: warns about missing/new labels
    """

    current = set(label2id.keys())

    if not os.path.isfile(labels_txt):

        with open(labels_txt, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(current)))

        print(
            f"[labels] Created reference "
            f"{labels_txt} with {len(current)} labels."
        )

        return

    with open(labels_txt, "r", encoding="utf-8") as f:
        reference = set(f.read().split())

    missing = reference - current
    new = current - reference

    if not missing and not new:

        print(
            f"[labels] OK — all "
            f"{len(current)} labels match {labels_txt}"
        )

    else:

        if missing:
            print(
                f"[labels] WARNING — "
                f"{len(missing)} label(s) missing:\n  "
                + ", ".join(sorted(missing))
            )

        if new:
            print(
                f"[labels] WARNING — "
                f"{len(new)} new label(s):\n  "
                + ", ".join(sorted(new))
            )


def main():

    parser = argparse.ArgumentParser(
        description="Convert ALTO4 XML annotations to COCO JSON"
    )

    parser.add_argument(
        "data_dir",
        help="Directory containing ALTO4 XML files"
    )

    parser.add_argument(
        "--labels_txt",
        default="labels.txt",
        help="Shared labels file for consistency checks"
    )

    args = parser.parse_args()

    # Recursive XML search
    ann_paths = sorted(
        p for p in glob.glob(
            os.path.join(args.data_dir, "**", "*.xml"),
            recursive=True
        )
        if os.path.basename(p) != "METS.xml"
    )

    if not ann_paths:
        raise SystemExit(
            f"No .xml files found in {args.data_dir}"
        )

    print(
        f"Found {len(ann_paths)} XML files. "
        f"Collecting labels..."
    )

    label2id = collect_labels(ann_paths)

    print(
        f"Found {len(label2id)} categories: "
        f"{', '.join(sorted(label2id))}"
    )

    check_labels(label2id, args.labels_txt)

    output_path = os.path.join(args.data_dir, "coco.json")

    convert_altos_to_cocojson(
        ann_paths,
        label2id,
        output_path
    )


if __name__ == "__main__":
    main()