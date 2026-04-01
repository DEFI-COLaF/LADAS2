import os
from lxml import etree
import glob
import click

ns = {"alto":"http://www.loc.gov/standards/alto/ns-v4#"}

@click.command()
def metrics_count():
    metrics_zone = {}
    for filename in glob.glob("*/*/*.xml"):
        if filename!="METS.xml" and 'xml' in filename:
            tree = etree.parse(filename)
            root = tree.getroot()
            tags = root.findall(".//alto:Tags/alto:OtherTag", namespaces=ns)
            for zone in root.findall(".//alto:TextBlock", namespaces=ns):
                if zone.attrib.get('TAGREFS'):
                    for tag in tags:
                        if tag.attrib['ID'] in zone.attrib['TAGREFS']:
                            metrics_zone[tag.attrib['LABEL']] = metrics_zone.get(tag.attrib['LABEL'], 0) + 1
                else:
                    metrics_zone[None] = metrics_zone.get(None, 0) + 1
                    print(f"{filename}: {zone.attrib['ID']} has no tags")
    for tag, count in metrics_zone.items():
        print(f"{tag}: {count}")
if __name__ == "__main__":
    metrics_count()
