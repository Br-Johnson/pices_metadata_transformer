"""Offline contracts for the v2 wire mapping (ADR 0014): FGDC content as structured Zenodo fields.

Synthetic FGDC fragments exercise each rule; one real prepared source checks the whole record
against the pinned InvenioRDM schema. No network, token or production state.
"""

import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts import modern_bulk as bulk
from scripts import modern_wire_v2 as wire_v2
from scripts.modern_singleton import Held, parse
from scripts.path_config import OutputPaths
from tests import modern_singleton_fixtures as fixtures


def fgdc(idinfo='', rest='', metd='20030115'):
    return ('<metadata><idinfo><citation><citeinfo><title>T</title></citeinfo></citation>' + idinfo
            + '</idinfo>' + rest + '<metainfo><metd>' + metd + '</metd></metainfo></metadata>').encode()


def root(idinfo='', rest='', metd='20030115'):
    return ET.fromstring(fgdc(idinfo, rest, metd))


class DateRules(unittest.TestCase):
    def test_exact_dates_and_everything_else(self):
        cases = {'1999': '1999', '199907': '1999-07', '19990731': '1999-07-31', '122003': '2003-12',
                 'March 1987': '1987-03', 'Sept. 2001': None, 'Sep 2001': '2001-09', '19990231': None,
                 'Unknown': None, '1700': None, '2031': None, '199913': None, '': None, 'unpublished': None}
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(wire_v2.exact_date(value), expected)

    def test_publication_date_prefers_an_exact_citation_date(self):
        cited = '<citation><citeinfo><pubdate>19870301</pubdate></citeinfo></citation>'
        self.assertEqual(wire_v2.publication_date(root(cited)), ('1987-03-01', 'citation'))
        vague = '<citation><citeinfo><pubdate>Unknown</pubdate></citeinfo></citation>'
        self.assertEqual(wire_v2.publication_date(root(vague)), ('2003-01-15', 'metadata'))
        with self.assertRaises(Held):
            wire_v2.publication_date(root(vague, metd='sometime'))

    def test_time_period_becomes_a_collected_date_or_stays_as_text(self):
        span = ('<timeperd><timeinfo><rngdates><begdate>19800601</begdate><enddate>1981</enddate></rngdates>'
                '</timeinfo><current>ground condition</current></timeperd>')
        dates, unparsed = wire_v2.time_period(root(span))
        self.assertEqual(dates, [{'date': '1980-06-01/1981', 'type': {'id': 'collected'},
                                  'description': 'Time period of content (ground condition)'}])
        self.assertEqual(unparsed, [])
        reversed_span = span.replace('19800601', '19830601')
        self.assertEqual(wire_v2.time_period(root(reversed_span)), ([], ['Time period: 19830601 to 1981']))
        multiple = ('<timeperd><timeinfo><mdattim><sngdate><caldate>1990</caldate></sngdate>'
                    '<sngdate><caldate>198802</caldate></sngdate></mdattim></timeinfo></timeperd>')
        dates, _ = wire_v2.time_period(root(multiple))
        self.assertEqual(dates[0]['date'], '1988-02/1990')
        self.assertIn('2 dates within this span', dates[0]['description'])
        begun = '<timeperd><timeinfo><rngdates><begdate>19680101</begdate><enddate></enddate></rngdates></timeinfo></timeperd>'
        dates, _ = wire_v2.time_period(root(begun))
        self.assertEqual(dates[0]['date'], '1968-01-01')
        self.assertTrue(dates[0]['description'].endswith('begin date only, no end date in the FGDC record'))
        vague = '<timeperd><timeinfo><sngdate><caldate>Unknown</caldate></sngdate></timeinfo></timeperd>'
        self.assertEqual(wire_v2.time_period(root(vague)), ([], ['Time period: Unknown']))


class LocationRules(unittest.TestCase):
    def box(self, west, east, north, south):
        return root('<spdom><bounding><westbc>%s</westbc><eastbc>%s</eastbc><northbc>%s</northbc>'
                    '<southbc>%s</southbc></bounding></spdom>' % (west, east, north, south))

    def test_box_point_and_antimeridian(self):
        [feature], note = wire_v2.bounding_box(self.box(-170, -150, 60, 50))
        self.assertIsNone(note)
        self.assertEqual(feature['geometry']['type'], 'Polygon')
        self.assertEqual(feature['geometry']['coordinates'][0][0], [-170.0, 50.0])
        [point], _ = wire_v2.bounding_box(self.box(-150, -150, 55, 55))
        self.assertEqual(point['geometry'], {'type': 'Point', 'coordinates': [-150.0, 55.0]})
        crossing, _ = wire_v2.bounding_box(self.box(160, -160, 60, 50))  # Zenodo refuses MultiPolygon
        self.assertEqual([f['geometry']['type'] for f in crossing], ['Polygon', 'Polygon'])
        self.assertEqual([f['geometry']['coordinates'][0][1][0] for f in crossing], [180.0, -160.0])
        self.assertEqual([f['description'][-28:] for f in crossing],
                         ['; part west of the date line', '; part east of the date line'])

    def test_unusable_boxes_stay_as_text(self):
        self.assertEqual(wire_v2.bounding_box(root()), ([], None))
        features, note = wire_v2.bounding_box(self.box(-170, -150, 50, 60))  # south above north
        self.assertEqual(features, [])
        self.assertEqual(note, 'Bounding coordinates as given: W -170, E -150, N 50, S 60')
        self.assertEqual(wire_v2.bounding_box(self.box('x', -150, 60, 50))[0], [])
        self.assertEqual(wire_v2.bounding_box(self.box(0, 0, 0, 0)),
                         ([], 'Bounding coordinates as given: W 0, E 0, N 0, S 0'))
        [equator], _ = wire_v2.bounding_box(self.box(-140, -140, 0, 0))  # FGDC-940: a mooring at 0N 140W
        self.assertEqual(equator['geometry'], {'type': 'Point', 'coordinates': [-140.0, 0.0]})

    def test_the_date_line_meridian_and_line_shaped_boxes(self):
        [edge], _ = wire_v2.bounding_box(self.box(180, -166, 66, 60))  # FGDC-2632: starts at the date line
        self.assertEqual(edge['geometry']['coordinates'][0][:2], [[-180.0, 60.0], [-166.0, 60.0]])
        for west, east in ((180, -180), (-180, -180)):  # FGDC-3775 and FGDC-3969: the whole globe
            [globe], _ = wire_v2.bounding_box(self.box(west, east, 90, -90))
            self.assertEqual(globe['geometry']['coordinates'][0][:2], [[-180.0, -90.0], [180.0, -90.0]])
        for box in ((-130.91, -130.91, 42.9, 8.49), (-150, -140, 55, 55)):  # FGDC-3859: a meridian segment
            self.assertEqual(wire_v2.bounding_box(self.box(*box))[0], [])
        [point], _ = wire_v2.bounding_box(self.box(-130.91, -130.91, 42.9, 42.9))
        self.assertEqual(point['geometry'], {'type': 'Point', 'coordinates': [-130.91, 42.9]})

    def test_a_box_kept_as_text_by_decision_has_no_map(self):
        box = self.box(171.2, 171.2, 57.1, 57.1)
        self.assertEqual(len(wire_v2.bounding_box(box)[0]), 1)
        self.assertEqual(wire_v2.bounding_box(box, as_text=True),
                         ([], 'Bounding coordinates as given: W 171.2, E 171.2, N 57.1, S 57.1'))
        self.assertEqual(wire_v2.bounding_box(root(), as_text=True), ([], None))

    def test_swapped_date_line_box_is_not_a_world_map(self):
        swapped, note = wire_v2.bounding_box(self.box(-176.42, -177.78, 58, 55))  # FGDC-2324: a 358 degree span
        self.assertEqual(swapped, [])
        self.assertEqual(note, 'Bounding coordinates as given: W -176.42, E -177.78, N 58, S 55')
        basin, _ = wire_v2.bounding_box(self.box(100, -75.76, 60, 20))  # FGDC-3740: the North Pacific, 184 degrees
        self.assertEqual(len(basin), 2)


class ContactRules(unittest.TestCase):
    def test_names_and_organisations_only(self):
        contacts = ('<ptcontac><cntinfo><cntperp><cntper>Smith, Jane</cntper><cntorg>NOAA</cntorg></cntperp>'
                    '<cntemail>jane@example.org</cntemail><cntvoice>555</cntvoice></cntinfo></ptcontac>')
        distributor = ('<distinfo><distrib><cntinfo><cntorgp><cntorg>National Ice Center</cntorg></cntorgp>'
                       '<cntaddr><address>1 Road</address></cntaddr></cntinfo></distrib></distinfo>')
        entries = wire_v2.contributors(root(contacts, distributor), [])
        self.assertEqual(entries, [
            {'person_or_org': {'type': 'personal', 'family_name': 'Smith', 'given_name': 'Jane'},
             'role': {'id': 'contactperson'}, 'affiliations': [{'name': 'NOAA'}]},
            {'person_or_org': {'type': 'organizational', 'name': 'National Ice Center'},
             'role': {'id': 'distributor'}}])
        self.assertNotIn('example.org', json.dumps(entries))

    def test_contact_type_follows_its_element(self):
        organisation = ('<ptcontac><cntinfo><cntorgp><cntorg>Fisheries and Oceans Canada, Pacific Region, Institute of'
                        ' Ocean Sciences</cntorg></cntorgp></cntinfo></ptcontac>')
        self.assertEqual(wire_v2.contributors(root(organisation), [])[0]['person_or_org'],
                         {'type': 'organizational',
                          'name': 'Fisheries and Oceans Canada, Pacific Region, Institute of Ocean Sciences'})
        natural = ('<ptcontac><cntinfo><cntperp><cntper>C.S. Wong</cntper><cntorg>Institute of Ocean Sciences</cntorg>'
                   '</cntperp></cntinfo></ptcontac>')
        entry = wire_v2.contributors(root(natural), [])[0]
        self.assertEqual((entry['person_or_org'], entry['affiliations']),
                         ({'type': 'personal', 'family_name': 'Wong', 'given_name': 'C.S.'},
                          [{'name': 'Institute of Ocean Sciences'}]))
        desk = '<ptcontac><cntinfo><cntperp><cntper>NOAA Central Library</cntper></cntperp></cntinfo></ptcontac>'
        self.assertEqual(wire_v2.contributors(root(desk), [])[0]['person_or_org'],
                         {'type': 'organizational', 'name': 'NOAA Central Library'})

    def test_duplicates_role_words_and_garbled_names(self):
        same = ('<ptcontac><cntinfo><cntorgp><cntorg>PMEL Office</cntorg></cntorgp></cntinfo></ptcontac>')
        again = '<distinfo><distrib><cntinfo><cntorgp><cntorg>PMEL Office</cntorg></cntorgp></cntinfo></distrib></distinfo>'
        self.assertEqual(len(wire_v2.contributors(root(same, again), [])), 1)
        role = ('<ptcontac><cntinfo><cntperp><cntper>Librarian</cntper><cntorg>NOAA Library</cntorg></cntperp>'
                '</cntinfo></ptcontac>')
        self.assertEqual(wire_v2.contributors(root(role), [])[0]['person_or_org'],
                         {'type': 'organizational', 'name': 'NOAA Library'})
        garbled = '<ptcontac><cntinfo><cntperp><cntper>Br￼mmer, A.</cntper></cntperp></cntinfo></ptcontac>'
        self.assertEqual(wire_v2.contributors(root(garbled), []), [])


class RecordRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.paths = OutputPaths(str(fixtures.prepare_sources(Path(cls.temp.name), ids=['FGDC-1915'])),
                                'production')
        cls.base = bulk.member_now(cls.paths, 'FGDC-1915')
        cls.v1 = parse(cls.base.body)

    def test_whole_record_keeps_the_reviewed_fields_and_passes_the_schema(self):
        record = wire_v2.build(self.v1, self.base.xml, ['FGDC-1915'], 'dataset')
        meta, old = record['metadata'], self.v1['metadata']
        self.assertEqual(record['access'], {'record': 'public', 'files': 'public'})
        self.assertEqual(meta['title'], wire_v2.strip_suffix(old['title']))
        self.assertEqual(wire_v2.strip_suffix('Survey' + wire_v2.ARTIFACT_SUFFIX), 'Survey')
        self.assertEqual(wire_v2.strip_suffix('Survey - FGDC XML'), 'Survey - FGDC XML')
        self.assertEqual((meta['creators'], meta['description'], meta['publisher']),
                         (old['creators'], old['description'], 'Zenodo'))
        self.assertNotIn(wire_v2.METADATA_ONLY_TAG, [s['subject'] for s in meta['subjects']])
        self.assertEqual(len(meta['subjects']), len([s for s in old['subjects']
                                                     if s['subject'] != wire_v2.METADATA_ONLY_TAG]))
        self.assertIn('FGDC-1915', meta['additional_descriptions'][-1]['description'])
        self.assertNotIn('{', ''.join(d['description'] for d in meta['additional_descriptions']))
        wire_v2.validate(record)  # build validates too; this states the contract
        broken = json.loads(json.dumps(record))
        broken['metadata']['locations'] = {'features': [{'geometry': {'type': 'Polygon'}}]}
        with self.assertRaises(Held):
            wire_v2.validate(broken)
        multi = json.loads(json.dumps(record))
        multi['metadata']['locations'] = {'features': [{'geometry': {
            'type': 'MultiPolygon', 'coordinates': [[[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]]]}}]}
        with self.assertRaises(Held):  # valid GeoJSON, refused by Zenodo
            wire_v2.validate(multi)
        with self.assertRaises(Held):
            wire_v2.build(self.v1, self.base.xml, ['FGDC-1915'], 'software')

    def test_rights_and_links_from_constraints_and_online_links(self):
        constraints = ('<useconst>Cite the source.</useconst><accconst>None</accconst>'
                       '<citation><citeinfo><onlink>https://example.org/data</onlink><onlink>ftp site</onlink>'
                       '<othercit>Smith 1999</othercit></citeinfo></citation>')
        r = root(constraints)
        self.assertEqual(wire_v2.rights(r)[0]['description']['en'], 'Use constraints: Cite the source.\n'
                                                                    'Access constraints: None')
        self.assertIn('no license is granted', wire_v2.rights(r)[0]['title']['en'])
        self.assertEqual(wire_v2.links(r), ([{'identifier': 'https://example.org/data', 'scheme': 'url',
                                              'relation_type': {'id': 'describes'}}],
                                            ['Online link as given: ftp site']))
        self.assertEqual(wire_v2.references(r), [{'reference': 'Smith 1999'}])

    def test_email_addresses_in_new_free_text_point_to_the_xml(self):
        r = root('<useconst>Contact custodian (email: cswong@ios.bc.ca).</useconst>',
                 '<distinfo><stdorder><digform><digtopt><onlinopt><accinstr>Ask j.doe@pac.dfo-mpo.gc.ca</accinstr>'
                 '</onlinopt></digtopt></digform></stdorder></distinfo>')
        self.assertEqual(wire_v2.rights(r)[0]['description']['en'],
                         'Use constraints: Contact custodian (email: ' + wire_v2.EMAIL_MARK + ').')
        technical = wire_v2.additional_descriptions(r, ['FGDC-1'], [], 'metadata')[-1]['description']
        self.assertIn('Ordering: Ask ' + wire_v2.EMAIL_MARK, technical)
        self.assertNotIn('@', technical)

    def test_comparison_allows_only_the_provider_rewrites(self):
        record = wire_v2.build(self.v1, self.base.xml, ['FGDC-1915'], 'dataset')
        stored = json.loads(json.dumps(record['metadata']))
        stored['resource_type']['title'] = {'en': 'Dataset'}
        stored['languages'] = []
        wire_v2.compare(stored, record['metadata'])
        for key, value in (('publication_date', '1900'), ('resource_type', {'id': 'publication-report'}),
                           ('title', 'Other'), ('subjects', [])):
            changed = dict(stored, **{key: value})
            with self.subTest(key=key), self.assertRaises(Held):
                wire_v2.compare(changed, record['metadata'])
        with self.assertRaises(Held):
            wire_v2.compare(dict(stored, version='2'), record['metadata'])


class ClassificationManifest(unittest.TestCase):
    def test_pinned_types_cover_every_reviewed_record_with_two_values(self):
        types = bulk.resource_types()
        self.assertEqual(set(types.values()), set(wire_v2.RESOURCE_TYPES))
        self.assertEqual(len(types), 3914)  # the 3,830 first reviewed, FGDC-1939, FGDC-141, the 25 non-Exxon pairs, the creators64 sources
        document = json.loads(bulk.RESOURCE_TYPES_PATH.read_text())
        self.assertEqual(sum(document['counts'].values()), len(types))
        self.assertTrue(set(document['confidence_low']) <= set(types))


if __name__ == '__main__':
    unittest.main()
