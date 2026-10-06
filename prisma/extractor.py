"""Extrai somente da API loopback demo. Não aceita endpoints externos."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit,urlencode
from urllib.request import urlopen,Request,build_opener,ProxyHandler,HTTPRedirectHandler

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('Redirecionamentos não são permitidos no extrator demo.')

def extract(base_url='http://127.0.0.1:8787',out='snapshots'):
    parts=urlsplit(base_url)
    if (parts.scheme!='http' or parts.hostname!='127.0.0.1' or parts.username or parts.password
        or parts.path not in ('','/') or parts.query or parts.fragment):
        raise ValueError('Use somente http://127.0.0.1:PORTA, sem caminho ou credenciais.')
    base_url=base_url.rstrip('/')
    opener=build_opener(ProxyHandler({}),NoRedirect())
    def get(path,params=None):
        suffix='?'+urlencode(params) if params else ''
        with opener.open(Request(base_url+path+suffix,headers={'Accept':'application/json'}),timeout=10) as response:
            return json.load(response)
    manifest=get('/api/demo/meta')
    if manifest.get('synthetic') is not True:
        raise ValueError('A API não se identifica como sintética.')
    fingerprint=manifest['fingerprint']
    snapshots={}
    def checked_get(path,params):
        obj=get(path,params)
        if obj.get('meta',{}).get('synthetic') is not True or obj['meta'].get('dataset')!=fingerprint:
            raise ValueError('Snapshot misturado ou sem marcador sintético. Reinicie a extração.')
        return obj
    def pages(source,path,key):
        if not manifest['sources'][source]['available']:
            return None
        records=[];seen=set();params={'page_size':100,'page':1} if source=='core' else {'limit':100}
        while True:
            response=checked_get(path,params)
            records.extend(response[key])
            nxt=response['pagination']['next_page'] if source=='core' else (
                (response['paging']['next'] or {}).get('after') if source=='crm' else response['nextCursor'])
            if nxt is None:break
            if str(nxt) in seen:raise ValueError('Cursor ou página repetida.')
            seen.add(str(nxt))
            params['page' if source=='core' else 'cursor']=nxt
        ids=[r['id'] for r in records]
        if len(set(ids))!=len(ids):raise ValueError('IDs duplicados na extração.')
        return records
    snapshots['core']=pages('core','/api/demo/core/customers','data')
    snapshots['crm']=pages('crm','/api/demo/crm/contacts','results')
    snapshots['omnichannel']=pages('omnichannel','/api/demo/omnichannel/customers','items')
    snapshots['conversations']=pages('omnichannel','/api/demo/omnichannel/conversations','items')
    snapshots['messages']=None if snapshots['conversations'] is None else []
    for conversation in snapshots['conversations'] or []:
        path='/api/demo/omnichannel/conversations/'+conversation['id']+'/messages'
        params={'limit':100};seen=set()
        while True:
            response=checked_get(path,params);snapshots['messages'].extend(response['items'])
            nxt=response['nextCursor']
            if not nxt:break
            if nxt in seen:raise ValueError('Cursor repetido em mensagens.')
            seen.add(nxt);params['cursor']=nxt
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    if any((out/(name+'.jsonl')).exists() for name in snapshots) or (out/'manifest.json').exists():
        raise ValueError('A pasta de snapshots já contém uma extração. Use outra pasta para preservar a anterior.')
    counts={};checksums={}
    for name,records in snapshots.items():
        counts[name]=None if records is None else len(records)
        if records is None:continue  # Indisponível não vira arquivo vazio.
        path=out/(name+'.jsonl')
        raw=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records).encode('utf-8')
        path.write_bytes(raw);checksums[path.name]=hashlib.sha256(raw).hexdigest()
    result={'synthetic':True,'dataset':fingerprint,'sources':manifest['sources'],'counts':counts,'sha256':checksums}
    (out/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result
