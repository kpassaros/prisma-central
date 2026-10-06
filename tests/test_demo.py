import importlib.util
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen,Request
from prisma.generator import generate,reference
from prisma.service import Service,ApiError
from prisma.validation import check
from prisma.http_server import make_server
from prisma.extractor import extract

class DemoTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.data=self.root/'data';generate(self.data,24);self.api=Service(self.data)
    def tearDown(self):self.temp.cleanup()
    def test_deterministic(self):
        other=self.root/'other';generate(other,24)
        for f in ('manifest.json','ground_truth.json','prisma_demo.sqlite'):
            self.assertEqual((self.data/f).read_bytes(),(other/f).read_bytes())
    def test_seed_changes(self):
        manifest=generate(self.root/'other',24,99)
        self.assertNotEqual(manifest['fingerprint'],self.api.manifest['fingerprint'])
    def test_validate_scenarios(self):
        report=check(self.data);self.assertTrue(report['ok']);self.assertEqual(report['scenarios'],10)
    def test_integrity(self):
        with self.api.connect() as db:
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
    def test_company_scoped_ids(self):
        rows={r['id']:r for r in self.api.rows('core_customers')}
        a,b=rows['DEMO-CORE-00011'],rows['DEMO-CORE-00012']
        self.assertEqual(a['customer_id'],b['customer_id'])
        self.assertNotEqual(reference(a),reference(b))
    def test_core_pagination(self):
        found=[];page=1
        while page:
            r=self.api.dispatch('/api/demo/core/customers',{'page':[str(page)],'page_size':['7']})
            found.extend(r['data']);page=r['pagination']['next_page']
        self.assertEqual(len(found),24);self.assertEqual(len({r['id'] for r in found}),24)
    def test_company_filter(self):
        r=self.api.dispatch('/api/demo/core/customers',{'company_id':['DEMO-COMP-B']})
        self.assertEqual(r['pagination']['total'],12)
        self.assertTrue(all(x['company_id']=='DEMO-COMP-B' for x in r['data']))
    def test_cursor_pagination(self):
        for path,key in [('/api/demo/crm/contacts','results'),('/api/demo/omnichannel/customers','items')]:
            seen=[];params={'limit':['3']}
            while True:
                obj=self.api.dispatch(path,params);seen.extend(obj[key])
                nxt=(obj['paging']['next'] or {}).get('after') if key=='results' else obj['nextCursor']
                if not nxt:break
                params['cursor']=[nxt]
            self.assertEqual(len(seen),len({r['id'] for r in seen}))
            self.assertEqual(len(seen),23)
    def test_bad_cursors(self):
        for token in ['abc','!!!!','x'*1100]:
            with self.assertRaises(ApiError) as cm:self.api.dispatch('/api/demo/crm/contacts',{'cursor':[token]})
            self.assertEqual(cm.exception.status,400)
    def test_cursor_bound_to_route(self):
        obj=self.api.dispatch('/api/demo/crm/contacts',{'limit':['1']})
        token=obj['paging']['next']['after']
        with self.assertRaises(ApiError):self.api.dispatch('/api/demo/omnichannel/customers',{'limit':['1'],'cursor':[token]})
    def test_cursor_bound_to_filter(self):
        obj=self.api.dispatch('/api/demo/crm/contacts',{'limit':['1']});token=obj['paging']['next']['after']
        with self.assertRaises(ApiError):self.api.dispatch('/api/demo/crm/contacts',{'limit':['1'],'cursor':[token],
            'updated_since':['2026-01-14T00:00:00Z']})
    def test_incremental_filter(self):
        obj=self.api.dispatch('/api/demo/core/customers',{'updated_since':['2026-01-15T00:00:00Z']})
        self.assertEqual(len(obj['data']),1)
        equal=self.api.dispatch('/api/demo/core/customers',{'updated_since':['2026-01-15T09:00:00Z']})
        self.assertEqual(len(equal['data']),0)
    def test_timezone_normalization(self):
        a=self.api.dispatch('/api/demo/core/customers',{'updated_since':['2026-01-14T21:00:00-03:00']})
        b=self.api.dispatch('/api/demo/core/customers',{'updated_since':['2026-01-15T00:00:00Z']})
        self.assertEqual(a,b)
    def test_invalid_parameters(self):
        for query in [{'limit':['0']},{'limit':['101']},{'limit':['1','2']},{'limit':['-1']},
            {'password':['secret']},{'updated_since':['2026-01-14']},{'updated_since':['garbage']}]:
            with self.assertRaises(ApiError):self.api.dispatch('/api/demo/crm/contacts',query)
    def test_read_only(self):
        with self.assertRaises(ApiError) as cm:self.api.dispatch('/api/demo/core/customers',method='POST')
        self.assertEqual(cm.exception.status,405)
        with self.api.connect() as db:
            with self.assertRaises(sqlite3.OperationalError):db.execute('DELETE FROM companies')
    def test_ground_truth_not_exposed(self):
        with self.assertRaises(ApiError):self.api.dispatch('/api/demo/ground_truth')
        with self.api.connect() as db:
            tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        self.assertNotIn('ground_truth',tables)
    def test_messages(self):
        obj=self.api.dispatch('/api/demo/omnichannel/conversations/DEMO-CONV-00001/messages')
        self.assertEqual(len(obj['items']),3)
        self.assertEqual([x['sender'] for x in obj['items']],['customer','agent','system'])
    def test_missing_conversation(self):
        with self.assertRaises(ApiError) as cm:self.api.dispatch('/api/demo/omnichannel/conversations/DEMO-CONV-99999/messages')
        self.assertEqual(cm.exception.status,404)
    def test_snapshot_metadata(self):
        self.assertNotEqual(self.api.manifest['sources']['core']['snapshot_at'],self.api.manifest['sources']['omnichannel']['snapshot_at'])
        self.assertTrue(self.api.dispatch('/api/demo/crm/contacts')['meta']['synthetic'])
    def test_no_accidental_overwrite(self):
        with self.assertRaises(ValueError):generate(self.data,24)
        other=self.root/'foreign';other.mkdir();db=sqlite3.connect(other/'prisma_demo.sqlite');db.execute('CREATE TABLE real_data(id)');db.close()
        with self.assertRaises(ValueError):generate(other,24,force=True)
    def test_force_and_restart_guard(self):
        generate(self.data,24,43,force=True)
        with self.assertRaises(ApiError) as cm:self.api.dispatch('/health')
        self.assertEqual(cm.exception.status,409)
    def test_unavailable(self):
        for source in ['core','crm','omnichannel']:
            data=self.root/source;generate(data,24,unavailable=source);api=Service(data)
            suffix={'core':'core/customers','crm':'crm/contacts','omnichannel':'omnichannel/customers'}[source]
            with self.assertRaises(ApiError) as cm:api.dispatch('/api/demo/'+suffix)
            self.assertEqual(cm.exception.status,503);self.assertTrue(check(data)['ok'])
    def test_sql_injection_is_data(self):
        obj=self.api.dispatch('/api/demo/core/customers',{'company_id':["' OR 1=1 --"]})
        self.assertEqual(obj['data'],[])
    def test_extractor_rejects_remote(self):
        for url in ['https://api.example.test','http://example.test','http://user:pw@127.0.0.1:8787',
            'http://127.0.0.1:8787/api','http://127.0.0.1:8787?token=x']:
            with self.assertRaises(ValueError):extract(url,self.root/'exports')
    def test_http_and_extraction(self):
        server=make_server(self.data,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(url+'/health',timeout=3) as r:self.assertTrue(json.load(r)['synthetic'])
            with self.assertRaises(HTTPError) as cm:urlopen(Request(url+'/health',method='POST'),timeout=3)
            self.assertEqual(cm.exception.code,405)
            with self.assertRaises(HTTPError) as cm:urlopen(url+'/api/demo/crm/contacts?limit=101',timeout=3)
            self.assertEqual(cm.exception.code,400)
            result=extract(url,self.root/'snapshots')
            self.assertEqual(result['counts']['core'],24);self.assertEqual(result['counts']['crm'],23)
            self.assertEqual(result['counts']['messages'],60)
            self.assertEqual(len(result['sha256']),5)
            with self.assertRaises(ValueError):extract(url,self.root/'snapshots')
        finally:server.shutdown();server.server_close();thread.join()
    def test_unavailable_extract_does_not_write_empty(self):
        data=self.root/'unavailable';generate(data,24,unavailable='crm');server=make_server(data,0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            out=self.root/'snapshots';result=extract(f'http://127.0.0.1:{server.server_port}',out)
            self.assertIsNone(result['counts']['crm']);self.assertFalse((out/'crm.jsonl').exists())
        finally:server.shutdown();server.server_close();thread.join()

@unittest.skipUnless(all(importlib.util.find_spec(p) for p in ['fastapi','httpx']), 'Dependências opcionais FastAPI não instaladas')
class FastAPITests(unittest.TestCase):
    def test_contract_and_openapi(self):
        from fastapi.testclient import TestClient
        from prisma.fastapi_app import create_app
        with tempfile.TemporaryDirectory() as temp:
            generate(temp,24);client=TestClient(create_app(temp))
            self.assertEqual(client.get('/health').status_code,200)
            self.assertEqual(client.get('/api/demo/crm/contacts?limit=0').status_code,400)
            self.assertEqual(client.post('/api/demo/crm/contacts').status_code,405)
            self.assertEqual(client.get('/api/demo/omnichannel/conversations/DEMO-CONV-00001/messages').status_code,200)
            schema=client.get('/openapi.json').json();self.assertEqual(len(schema['paths']),8)
            self.assertEqual(client.get('/docs').status_code,200)

if __name__=='__main__':unittest.main()
