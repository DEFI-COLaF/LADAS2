#!/usr/bin/env python3
"""
Update all ALTO XML files to change fileIdentifier to ../image/filename.jpg
"""

import os
from pathlib import Path
from lxml import etree

workspace_root = Path("/home/jjanes/Documents/4_LADaS/LADAS2-REVIEW/train_ladas/alto/")
ns = {"alto": "http://www.loc.gov/standards/alto/ns-v4#"}

# Find all XML files (ALTO files) in all subdirectories
xml_files = list(workspace_root.glob("**/*.xml"))
ns = {"alto": "http://www.loc.gov/standards/alto/ns-v4#"}

# Find all XML files (ALTO files) in all subdirectories
xml_files = list(workspace_root.glob("*/*.xml"))

print(f"Found {len(xml_files)} ALTO XML files\n")

updated_count = 0
error_count = 0

for xml_file in sorted(xml_files):
    try:
        tree = etree.parse(str(xml_file))
        root = tree.getroot()
        
        # Find fileIdentifier elements
        file_identifiers = root.findall(".//alto:fileIdentifier", namespaces=ns)
        
        if file_identifiers:
            for file_id_elem in file_identifiers:
                old_path = file_id_elem.text
                
                # Get the filename from the sourceImageInformation/fileName element
                file_names = root.findall(".//alto:fileName", namespaces=ns)
                if file_names and file_names[0].text:
                    image_name = file_names[0].text
                    # Update to ../image/filename
                    new_path = f"../image/{image_name}"
                    file_id_elem.text = new_path
                    print(f"✓ {xml_file.name}")
                    print(f"  {old_path}")
                    print(f"  → {new_path}\n")
                    updated_count += 1
            
            # Write the modified XML back
            tree.write(str(xml_file), pretty_print=True, xml_declaration=True, 
                      encoding='UTF-8', standalone=True)
    
    except Exception as e:
        print(f"✗ Error processing {xml_file.name}: {e}\n")
        error_count += 1

print(f"\n{'='*60}")
print(f"Total files updated: {updated_count}")
print(f"Errors: {error_count}")
print(f"{'='*60}")
