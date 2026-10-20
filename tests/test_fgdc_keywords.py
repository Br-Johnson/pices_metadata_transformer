"""Keyword extraction keeps the whole text of marked-up keywords (CO<sub>2</sub>), and plain ones unchanged."""

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.fgdc_to_zenodo import FGDCToZenodoTransformer

REPO = Path(__file__).resolve().parents[1]
CO2_SOURCES = ('FGDC-277', 'FGDC-1258', 'FGDC-1266', 'FGDC-1939', 'FGDC-2562', 'FGDC-3513', 'FGDC-3514',
               *(f'FGDC-{n}' for n in range(3610, 3618)), *(f'FGDC-{n}' for n in range(3620, 3630)))


class KeywordTextTests(unittest.TestCase):
    def setUp(self):
        with patch('scripts.fgdc_to_zenodo.get_logger', return_value=Mock()):
            self.transformer = FGDCToZenodoTransformer()

    def keywords(self, xml):
        return self.transformer._extract_keywords(ET.fromstring(xml), 'fixture')

    def test_pretty_printed_subscript_is_joined(self):
        xml = ('<metadata><idinfo><keywords><theme><themekt>None</themekt><themekey>\r\n  Carbon Dioxide (CO\r\n'
               '  <sub>2</sub>\r\n  )\r\n</themekey></theme></keywords></idinfo></metadata>')
        self.assertEqual(self.keywords(xml), ['Carbon Dioxide (CO2)'])

    def test_plain_keywords_keep_their_former_text(self):
        xml = ('<metadata><idinfo><keywords><theme><themekey> Melanitta  spp. </themekey><themekey>Fish</themekey>'
               '</theme><place><placekey>Bering Sea</placekey><placekey>Fish</placekey></place></keywords>'
               '</idinfo></metadata>')
        self.assertEqual(self.keywords(xml), ['Melanitta  spp.', 'Fish', 'Bering Sea'])

    def test_a_word_after_a_subscript_keeps_its_space(self):
        element = ET.fromstring('<themekey>CO<sub>2</sub> flux and CO<sub>2</sub>-rich water</themekey>')
        self.assertEqual(FGDCToZenodoTransformer._element_text(element), 'CO2 flux and CO2-rich water')

    def test_other_inline_markup_keeps_word_spacing(self):
        element = ET.fromstring('<themekey>Sea <i>surface</i> temperature</themekey>')
        self.assertEqual(FGDCToZenodoTransformer._element_text(element), 'Sea surface temperature')

    def test_every_marked_up_source_keyword_is_whole(self):
        for source_id in CO2_SOURCES:
            with self.subTest(source_id=source_id):
                root = ET.parse(REPO / 'FGDC' / (source_id + '.xml')).getroot()
                keywords = self.transformer._extract_keywords(root, source_id)
                self.assertIn('Carbon Dioxide (CO2)', keywords)
                self.assertNotIn('Carbon Dioxide (CO', keywords)


if __name__ == '__main__':
    unittest.main()
