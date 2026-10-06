"""Contrato do build público: pipeline real, somente fontes sintéticas."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
builder=module('prisma_site_builder',ROOT/'scripts/build_site.py')
auditor=module('prisma_site_auditor',ROOT/'scripts/audit_site.py')
class StaticSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)/'public'
        cls.report=builder.build(cls.root)
        cls.data=json.loads((cls.root/'data/demo.json').read_text(encoding='utf-8'))
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_public_allowlist_and_equivalence(self):
        self.assertTrue(auditor.audit(self.root)['baseline_python_equivalence'])
    def test_four_real_synthetic_builds(self):
        self.assertEqual(set(self.data['scenarios']),set(builder.SCENARIOS))
        self.assertEqual(self.data['scenarios']['normal']['overview']['counts']['core'],120)
    def test_core_absent_is_not_zero(self):
        s=self.data['scenarios']['core-off'];self.assertIsNone(s['overview']['core_metrics']);self.assertIsNone(s['reconciliation']);self.assertIsNone(s['overview']['counts']['core'])
    def test_crm_absent_has_no_residual_rows(self):
        s=self.data['scenarios']['crm-off'];self.assertIsNone(s['records']['crm']);self.assertIsNone(s['raw']['crm']);self.assertEqual(s['reconciliation'][0]['crm']['status'],'not_evaluated')
    def test_omni_absent_has_no_messages(self):
        s=self.data['scenarios']['omni-off'];self.assertIsNone(s['records']['conversations']);self.assertIsNone(s['records']['messages'])
    def test_raw_and_normalized_contracts_preserved(self):
        s=self.data['scenarios']['normal'];self.assertIn('properties',s['raw']['crm'][0]);self.assertIn('core_reference',s['records']['crm'][0]);self.assertEqual(s['overview']['core_metrics']['reference_both'],110)
    def test_relative_assets_and_no_bootstrap(self):
        html=(self.root/'index.html').read_text();self.assertNotIn('__BOOTSTRAP__',html);self.assertIn('./assets/adapter.js',html);self.assertNotIn('src="/',html)
    def test_unknown_destination_not_overwritten(self):
        bad=Path(self.temp.name)/'user-files';bad.mkdir();(bad/'notes.txt').write_text('keep')
        with self.assertRaises(ValueError):builder.build(bad)
        self.assertEqual((bad/'notes.txt').read_text(),'keep')
    def test_project_root_not_overwritten(self):
        with self.assertRaises(ValueError):builder.build(ROOT)
    def test_tampered_public_file_rejected(self):
        f=self.root/'assets/adapter.js';original=f.read_bytes();f.write_bytes(original+b'\n// tamper')
        try:
            with self.assertRaises(ValueError):auditor.audit(self.root)
        finally:f.write_bytes(original)
    def test_source_application_not_changed(self):
        source=(ROOT/'prisma/web/app.js').read_text();self.assertIn('X-Prisma-Demo-Token',source);self.assertNotIn('window.PrismaStatic',source)
