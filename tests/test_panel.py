import hashlib
import json
import re
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen,Request
from prisma.generator import generate
from prisma.http_server import make_server
from prisma.extractor import extract
from prisma.panel import SnapshotPanel,PanelError,make_panel_server

class PanelTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        generate(self.root/'data',24)
        self.snapshots=self.root/'snapshots';self.extract(self.root/'data',self.snapshots)
        self.panel=SnapshotPanel(self.snapshots)
    def tearDown(self):self.temp.cleanup()
    def extract(self,data,out):
        server=make_server(data,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:extract(f'http://127.0.0.1:{server.server_port}',out)
        finally:server.shutdown();server.server_close();thread.join()
    def tamper(self,name,change,update_hash=False):
        p=self.snapshots/name;raw=p.read_bytes();raw=change(raw);p.write_bytes(raw)
        if update_hash:
            path=self.snapshots/'manifest.json';manifest=json.loads(path.read_text());manifest['sha256'][name]=hashlib.sha256(raw).hexdigest();path.write_text(json.dumps(manifest))
    def test_load_and_reconcile(self):
        overview=self.panel.overview();self.assertEqual(overview['core_metrics'],{'total':24,'reference_both':14,'review':7})
        for source in ['crm','omnichannel']:
            self.assertEqual(overview['results'][source],{'confirmed_by_reference':14,'candidate':2,'conflict':5,'not_comparable':2,'not_found':1})
    def test_no_database_required(self):
        shutil.rmtree(self.root/'data')
        self.assertEqual(SnapshotPanel(self.snapshots).overview()['counts']['core'],24)
    def test_records_mask_and_reveal(self):
        masked=self.panel.dispatch('/api/panel/records',{'source':['crm']})
        self.assertTrue(all(r['name']=='P***' for r in masked['rows']))
        visible=self.panel.dispatch('/api/panel/records',{'source':['crm'],'reveal':['1']})
        self.assertTrue(visible['rows'][0]['name'].startswith('Pessoa'))
    def test_record_issues_and_search(self):
        obj=self.panel.dispatch('/api/panel/records',{'source':['core'],'issue':['invalid_email'],'reveal':['1']})
        self.assertEqual(obj['total'],1);self.assertEqual(obj['rows'][0]['email'],'EMAIL-DEMO-INVALIDO')
        empty=self.panel.dispatch('/api/panel/records',{'search':['NOT-EXISTS']})
        self.assertEqual(empty['total'],0)
    def test_evidence_preserves_multiple_candidates(self):
        obj=self.panel.dispatch('/api/panel/evidence',{'id':['DEMO-CORE-00010']})
        self.assertEqual(obj['crm']['status'],'conflict');self.assertEqual(len(obj['crm']['candidates']),2)
        self.assertTrue(any(k['kind']=='core_reference' for c in obj['crm']['candidates'] for k in c['keys']))
    def test_contact_candidate(self):
        obj=self.panel.dispatch('/api/panel/evidence',{'id':['DEMO-CORE-00002']})
        self.assertEqual(obj['crm']['status'],'candidate')
    def test_company_scoped_key(self):
        a=self.panel.dispatch('/api/panel/evidence',{'id':['DEMO-CORE-00011']})
        b=self.panel.dispatch('/api/panel/evidence',{'id':['DEMO-CORE-00012']})
        self.assertEqual(a['customer_id'],b['customer_id']);self.assertNotEqual(a['core_reference'],b['core_reference'])
    def test_status_filter(self):
        obj=self.panel.dispatch('/api/panel/reconciliation',{'status':['conflict']})
        self.assertEqual(obj['total'],5)
    def test_pagination(self):
        obj=self.panel.dispatch('/api/panel/records',{'page':['2'],'size':['5']})
        self.assertEqual(obj['page'],2);self.assertEqual(obj['pages'],5);self.assertEqual(len(obj['rows']),5)
    def test_hash_tamper(self):
        self.tamper('core.jsonl',lambda raw:raw+b'\n')
        with self.assertRaisesRegex(PanelError,'SHA-256'):SnapshotPanel(self.snapshots)
    def test_synthetic_contract_even_when_hash_updated(self):
        self.tamper('crm.jsonl',lambda raw:raw.replace(b'@example.test',b'@example.com'),True)
        with self.assertRaisesRegex(PanelError,'reservado'):SnapshotPanel(self.snapshots)
    def test_real_name_rejected_even_with_updated_hash(self):
        def edit(raw):
            lines=raw.decode().splitlines();row=json.loads(lines[0]);row['name']='Nome não sintético';lines[0]=json.dumps(row);return ('\n'.join(lines)+'\n').encode()
        self.tamper('core.jsonl',edit,True)
        with self.assertRaisesRegex(PanelError,'Nome fora'):SnapshotPanel(self.snapshots)
    def test_symlink_rejected(self):
        path=self.snapshots/'core.jsonl';target=self.root/'outside.jsonl';path.rename(target);path.symlink_to(target)
        with self.assertRaisesRegex(PanelError,'link não permitido'):SnapshotPanel(self.snapshots)
    def test_manifest_traversal_rejected(self):
        path=self.snapshots/'manifest.json';m=json.loads(path.read_text());m['sha256']['../.env']='0'*64;path.write_text(json.dumps(m))
        with self.assertRaisesRegex(PanelError,'arquivo não permitido'):SnapshotPanel(self.snapshots)
    def test_manifest_counts_checked(self):
        path=self.snapshots/'manifest.json';m=json.loads(path.read_text());m['counts']['core']=1;path.write_text(json.dumps(m))
        with self.assertRaisesRegex(PanelError,'Contagem não confere'):SnapshotPanel(self.snapshots)
    def test_unknown_and_invalid_query(self):
        for q in [{'source':['real']},{'size':['0']},{'reveal':['true']},{'search':['x','y']},{'private_path':['/etc/passwd']}]:
            with self.assertRaises(PanelError):self.panel.dispatch('/api/panel/records',q)
    def test_unavailable(self):
        for source in ['core','crm','omnichannel']:
            generate(self.root/source,24,unavailable=source);out=self.root/('snapshots-'+source);self.extract(self.root/source,out);panel=SnapshotPanel(out)
            self.assertIsNone(panel.overview()['sources'][source]['profile'])
            if source=='core':
                self.assertFalse(panel.dispatch('/api/panel/reconciliation')['available'])
                self.assertIsNone(panel.overview()['core_metrics'])
            else:
                self.assertTrue(all(r[source]['status']=='not_evaluated' for r in panel.reconciled))
                with self.assertRaises(PanelError) as cm:panel.dispatch('/api/panel/records',{'source':[source]})
                self.assertEqual(cm.exception.status,503)
    def test_stale_unavailable_file_rejected(self):
        path=self.snapshots/'manifest.json';m=json.loads(path.read_text());m['sources']['crm']['available']=False;m['counts']['crm']=None;path.write_text(json.dumps(m))
        with self.assertRaisesRegex(PanelError,'residual'):SnapshotPanel(self.snapshots)
    def test_conversations_and_messages(self):
        obj=self.panel.dispatch('/api/panel/conversations');self.assertEqual(obj['total'],20)
        messages=self.panel.dispatch('/api/panel/messages',{'id':['DEMO-CONV-00001']});self.assertEqual(len(messages['rows']),3)
    def test_http_token_host_and_read_only(self):
        server=make_panel_server(self.snapshots,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url=f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(url) as response:
                html=response.read().decode();self.assertIn('DEMO · 100% sintético',html);self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
            match=re.search(r'window.PRISMA_DEMO_BOOT=(\{.*?\});',html);token=json.loads(match[1])['token']
            with self.assertRaises(HTTPError) as cm:urlopen(url+'/api/panel/overview')
            self.assertEqual(cm.exception.code,403)
            with urlopen(Request(url+'/api/panel/overview',headers={'X-Prisma-Demo-Token':token})) as response:self.assertTrue(json.load(response)['synthetic'])
            with self.assertRaises(HTTPError) as cm:urlopen(Request(url+'/health',headers={'Host':'evil.example.test'}))
            self.assertEqual(cm.exception.code,403)
            with self.assertRaises(HTTPError) as cm:urlopen(Request(url+'/api/panel/overview',method='POST'))
            self.assertEqual(cm.exception.code,405)
            with self.assertRaises(HTTPError) as cm:urlopen(url+'/.env')
            self.assertEqual(cm.exception.code,404)
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
