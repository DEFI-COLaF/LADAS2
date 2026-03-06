import os
from lxml import etree
import glob

ladas_vocabulary = ['DropCapitalZone','DigitizationArtefactZone', 
                    'FigureZone', 'FigureZone-Head', 
                    'FormZone', 'FormZone-Field', 'FormZone-Head', 'FormZone-Part',
                    'GraphicZone', 'GraphicZone-Decoration', 'GraphicZone-Head', 'GraphicZone-P', 'GraphicZone-Part', 'GraphicZone-Ab',
                    'MainZone-Ab', 'MainZone-Address', 'MainZone-Continued', 'MainZone-Dateline', 'MainZone-DropCapital', 
                    'MainZone-Head', 'MainZone-HeadStructured', 'MainZone-Item', 'MainZone-Lg', 'MainZone-Maths', 'MainZone-P', 
                    'MainZone-PLabelled', 'MainZone-PQuoted', 'MainZone-PStructured', 'MainZone-PStyled', 'MainZone-Signed', 
                    'MarginTextZone-Ab', 'MarginTextZone-Continued', 'MarginTextZone-Lg', 'MarginTextZone-ManuscriptAddendum',
                    'MarginTextZone-P', 'MarginTextZone-PLabelled', 'MarginTextZone-PStructured',
                    'MusicZone',
                    'NumberingZone',
                    'QuireMarksZone',
                    'RunningTitleZone', 
                    'StampZone',
                    'TableZone', 'TableZone-Head',
                    'TitlePageZone']

ns = {"alto":"http://www.loc.gov/standards/alto/ns-v4#"}

for filename in glob.glob("*/*.xml"):
    if filename!="METS.xml":
        tree = etree.parse(filename)
        root = tree.getroot()
        tags = root.findall(".//alto:Tags/alto:OtherTag", namespaces=ns)
        for tag in tags: 
            if tag.attrib['LABEL'] not in ladas_vocabulary:
                non_ladas_tag_id = tag.attrib['ID']
                present_in_doc = False
                for zone in root.findall(".//alto:TextBlock", namespaces=ns):
                    if not zone.attrib.get('TAGREFS'):
                        print(f"{filename}: {zone.attrib['ID']} has no TAGREFS attribute")
                    elif zone.attrib.get('TAGREFS') == non_ladas_tag_id:
                        print(f"{filename}: {zone.attrib['ID']} is tagged with {tag.attrib['LABEL']}, ID: {tag.attrib['ID']}")
                        present_in_doc = True
                if not present_in_doc:
                    tag.getparent().remove(tag)
                    tree.write(filename, pretty_print=True, xml_declaration=True, encoding='UTF-8')
                   