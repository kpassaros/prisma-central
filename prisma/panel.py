"""Painel público independente, alimentado SOMENTE por snapshots demo verificados."""
import hashlib
import hmac
import json
import math
import re
import secrets
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from .validation import email, phone, prepare, classify

SOURCES=('core','crm','omnichannel')
FILES={'core':'core.jsonl','crm':'crm.jsonl','omnichannel':'omnichannel.jsonl','conversations':'conversations.jsonl','messages':'messages.jsonl'}
LABELS={'core':'ERP Core','crm':'CRM','omnichannel':'Omnichannel'}
STATUSES={'confirmed_by_reference':'Pela referência','candidate':'Candidato','conflict':'Conflito',
 'not_found':'Não encontrado','not_comparable':'Não comparável','not_evaluated':'Não avaliado'}
ISSUES={'all':'Todos','missing_email':'Sem e-mail','invalid_email':'E-mail inválido','missing_phone':'Sem telefone',
 'shared_email':'E-mail compartilhado','missing_reference':'Sem referência Core'}
TEXTS=('Olá! Esta mensagem é inteiramente fictícia.',
 'Atendimento simulado do Prisma Demo. Nenhum cliente real.',
 'Cenário de portfólio: evento sintético de encaminhamento.')
WEB=Path(__file__).resolve().parent/'web'

class PanelError(ValueError):
    def __init__(self,message,status=400):
        super().__init__(message);self.status=status

def clean_json(raw):
    def invalid(value):raise ValueError('Número JSON não finito.')
    return json.loads(raw,parse_constant=invalid)

def instant(value):
    if not isinstance(value,str):raise PanelError('Timestamp ausente ou inválido no snapshot.')
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        if d.tzinfo is None:raise ValueError()
    except ValueError:raise PanelError('Timestamp do snapshot exige timezone.')
    return d

def valid_name(value):
    return isinstance(value,str) and (bool(re.fullmatch(r'Pessoa (Aurora|Horizonte|Cristal|Violeta|Solar|Lume) [0-9]{5}',value)) or value=='Pessoa Exclusiva Demo')

def native(row,source):
    try:
        if source=='core':
            keys=('id','company_id','customer_id','name','email','phone','document','city','updated_at')
            if set(row)!=set(keys):raise PanelError('Contrato Core incompatível com a demo 0.1.')
            if row['company_id'] not in ('DEMO-COMP-A','DEMO-COMP-B') or not re.fullmatch(r'DEMO-LOCAL-([0-9]{5}|COMMON)',row['customer_id']):
                raise PanelError('Chave Core fora do contrato fictício.')
            if row['document'] not in ('','00000000000') or not re.fullmatch(r'Cidade Fictícia [1-6]',row['city']):
                raise PanelError('Documento/localidade fora do contrato fictício.')
            result={**row,'core_reference':row['company_id']+'/'+row['customer_id']}
        elif source=='crm':
            if set(row)!= {'id','properties','updatedAt'}:raise PanelError('Contrato CRM incompatível.')
            p=row['properties']
            if set(p)!= {'firstname','lastname','email','phone','core_reference','lifecycle_stage'} or p['lastname']!='Sintética' or p['lifecycle_stage'] not in ('lead','qualified','customer'):
                raise PanelError('Propriedades CRM fora do contrato fictício.')
            result={'id':row['id'],'name':p['firstname'],'email':p['email'],'phone':p['phone'],
                'core_reference':p['core_reference'],'stage':p['lifecycle_stage'],'updated_at':row['updatedAt']}
        else:
            if set(row)!= {'id','name','contacts','customFields','channel','updatedAt'} or set(row['contacts'])!= {'email','phone'} or set(row['customFields'])!= {'core_reference'}:
                raise PanelError('Contrato Omnichannel incompatível.')
            if row['channel'] not in ('chat-demo','messenger-demo'):raise PanelError('Canal não sintético.')
            result={'id':row['id'],'name':row['name'],**row['contacts'],
                'core_reference':row['customFields']['core_reference'],'channel':row['channel'],'updated_at':row['updatedAt']}
        if not valid_name(result['name']):raise PanelError('Nome fora da convenção sintética. Dados operacionais não são aceitos.')
        e,p,ref=result['email'],result['phone'],result['core_reference']
        if not isinstance(e,str) or (e and e!='EMAIL-DEMO-INVALIDO' and not re.fullmatch(r'[a-z0-9.]+@example\.test',e.casefold())):
            raise PanelError('E-mail fora do domínio reservado da demo.')
        if not isinstance(p,str) or (p and not re.fullmatch(r'00[0-9]{9}',p)):
            raise PanelError('Telefone fora da convenção fictícia DDD 00.')
        if not isinstance(ref,str) or (ref and not re.fullmatch(r'DEMO-COMP-[AB]/DEMO-LOCAL-([0-9]{5}|COMMON)',ref)):
            raise PanelError('Referência fora do contrato demo.')
        instant(result['updated_at'])
        return result
    except (KeyError,TypeError):
        raise PanelError('Campos obrigatórios ausentes ou tipos inválidos no snapshot.')

class SnapshotPanel:
    def __init__(self,folder='snapshots'):
        folder=Path(folder).resolve();manifest_path=folder/'manifest.json'
        def read(name):
            path=folder/name
            if path.is_symlink() or path.resolve().parent!=folder or not path.is_file():
                raise PanelError('Snapshot obrigatório ausente ou link não permitido: '+name)
            if path.stat().st_size>50*1024*1024:raise PanelError('Snapshot maior que 50 MB; divida a demonstração.')
            return path.read_bytes()
        try:
            manifest_bytes=read('manifest.json');self.manifest=clean_json(manifest_bytes)
            m=self.manifest
            if m.get('synthetic') is not True or not re.fullmatch('[0-9a-f]{64}',m.get('dataset','')):
                raise PanelError('Manifesto não identificado como Prisma Demo sintético.')
            if set(m.get('sources',{}))!=set(SOURCES) or set(m.get('counts',{}))!=set(FILES):
                raise PanelError('Manifesto de fontes/contagens incompatível.')
            for source in SOURCES:
                src=m['sources'][source]
                if type(src['available']) is not bool:raise PanelError('Disponibilidade inválida.')
                instant(src['snapshot_at'])
            if not isinstance(m.get('sha256'),dict) or set(m['sha256'])-set(FILES.values()):
                raise PanelError('Lista de hashes contém arquivo não permitido.')
            self.raw={};self.rows={};self.hashes={}
            for kind,filename in FILES.items():
                source=kind if kind in SOURCES else 'omnichannel'
                available=m['sources'][source]['available']
                count=m['counts'][kind]
                if not available:
                    if count is not None or filename in m['sha256'] or (folder/filename).exists():
                        raise PanelError('Fonte indisponível com arquivo/contagem residual. Use uma extração nova.')
                    self.raw[kind]=None;self.rows[kind]=None;continue
                if type(count) is not int or not 0<=count<=100000:raise PanelError('Contagem inválida.')
                content=read(filename)
                expected=m['sha256'].get(filename,'')
                actual=hashlib.sha256(content).hexdigest()
                if not re.fullmatch('[0-9a-f]{64}',expected) or not hmac.compare_digest(actual,expected):
                    raise PanelError('Integridade SHA-256 divergente: '+filename+'. Faça nova extração.')
                records=[clean_json(line) for line in content.decode('utf-8').splitlines() if line.strip()]
                if len(records)!=count:raise PanelError('Contagem não confere com o manifesto: '+filename)
                ids=[]
                for r in records:
                    if not isinstance(r,dict) or not isinstance(r.get('id'),str) or not r['id'].startswith('DEMO-'):
                        raise PanelError('Registro sem ID sintético.')
                    ids.append(r['id'])
                if len(set(ids))!=len(ids):raise PanelError('IDs nativos duplicados no snapshot.')
                self.raw[kind]=records;self.rows[kind]=[native(r,kind) for r in records] if kind in SOURCES else records
                self.hashes[filename]=actual
            if read('manifest.json')!=manifest_bytes:raise PanelError('Manifesto mudou durante a carga. Reinicie com extração estável.')
            self.validate_relations()
            self.loaded_at=datetime.now(timezone.utc).isoformat()
            self.profiles={source:self.profile(source) for source in SOURCES}
            self.reconciled=self.reconcile()
        except PanelError:raise
        except (OSError,ValueError,TypeError,KeyError) as exc:
            raise PanelError('Snapshots incompatíveis. Extraia a demo 0.1 para uma pasta nova; nenhum dado operacional foi carregado.') from exc

    def validate_relations(self):
        core=self.rows['core']
        if core is not None:
            keys=[r['core_reference'] for r in core]
            if len(set(keys))!=len(keys):raise PanelError('Chave empresa/cliente Core duplicada.')
        if self.rows['omnichannel'] is None:return
        ids={r['id'] for r in self.rows['omnichannel']}
        conv=self.rows['conversations'];messages=self.rows['messages'];conv_ids={r['id'] for r in conv}
        for r in conv:
            if set(r)!= {'id','customer_id','status','channel','created_at','updated_at'} or r['customer_id'] not in ids or r['status'] not in ('open','closed') or r['channel'] not in ('chat-demo','messenger-demo'):
                raise PanelError('Relação/contrato de conversa fictícia inválido.')
            instant(r['created_at']);instant(r['updated_at'])
        for r in messages:
            if set(r)!= {'id','conversation_id','sender','text','created_at'} or r['conversation_id'] not in conv_ids or r['sender'] not in ('customer','agent','system') or r['text'] not in TEXTS:
                raise PanelError('Mensagem não sintética ou conversa de destino inexistente.')
            instant(r['created_at'])

    def profile(self,source):
        rows=self.rows[source]
        if rows is None:return None
        emails=Counter(email(r['email']) for r in rows if email(r['email']))
        result={'records':len(rows),'email_filled':sum(bool(r['email']) for r in rows),
            'email_syntax':sum(bool(email(r['email'])) for r in rows),
            'phone_filled':sum(bool(r['phone']) for r in rows),
            'shared_email_records':sum(emails.get(email(r['email']),0)>1 for r in rows),
            'reference_filled':sum(bool(r['core_reference']) for r in rows),
            'document_missing':sum(not r['document'] for r in rows) if source=='core' else None,
            'document_invalid':sum(bool(r['document']) for r in rows) if source=='core' else None}
        for r in rows:
            issues=[]
            if not r['email']:issues.append('missing_email')
            elif not email(r['email']):issues.append('invalid_email')
            if not r['phone']:issues.append('missing_phone')
            if emails.get(email(r['email']),0)>1:issues.append('shared_email')
            if source!='core' and not r['core_reference']:issues.append('missing_reference')
            r['issues']=issues
        result['issues']={key:sum(key in r['issues'] for r in rows) for key in ISSUES if key!='all'}
        return result

    def reconcile(self):
        core=self.rows['core']
        if core is None:return None
        result=[{'id':row['id'],'name':row['name'],'company_id':row['company_id'],
            'customer_id':row['customer_id'],'core_reference':row['core_reference']} for row in core]
        lookup={row['id']:row for row in result}
        for source in ('crm','omnichannel'):
            target=self.rows[source] or [];prepared=prepare(target,core)
            refs,emails,phones,core_emails,core_phones=prepared
            target_ids={r['id']:r for r in target}
            for row in core:
                item=lookup[row['id']]
                status=classify(row,target,core,self.rows[source] is not None,prepared)
                ev={}
                for kind,value,mapping,cmap in (('core_reference',row['core_reference'],refs,None),
                    ('email',email(row['email']),emails,core_emails),('phone',phone(row['phone']),phones,core_phones)):
                    if not value:continue
                    for ident in sorted(mapping.get(value,set())):
                        entry=ev.setdefault(ident,{'id':ident,'name':target_ids[ident]['name'],'keys':[]})
                        entry['keys'].append({'kind':kind,'value':value,
                            'core_occurrences':1 if kind=='core_reference' else len(cmap.get(value,set())),
                            'source_occurrences':len(mapping.get(value,set()))})
                item[source]={'status':status,'label':STATUSES[status],'candidates':list(ev.values())}
        return result

    def masked(self,row,reveal=False):
        r=json.loads(json.dumps(row))
        if reveal:return r
        def hide(item):
            if item.get('name'):item['name']=item['name'][:1]+'***'
            if item.get('email'):item['email']='***@example.test' if '@' in item['email'] else '***'
            if item.get('phone'):item['phone']='***'+item['phone'][-4:]
        hide(r)
        for source in ('crm','omnichannel'):
            if source in r:
                for c in r[source]['candidates']:
                    hide(c)
                    for key in c['keys']:
                        if key['kind']=='email':key['value']='***@example.test'
                        elif key['kind']=='phone':key['value']='***'+key['value'][-4:]
        return r

    def overview(self):
        return {'synthetic':True,'dataset':self.manifest['dataset'],'loaded_at':self.loaded_at,
            'sources':{s:{'label':LABELS[s],**self.manifest['sources'][s],
                'profile':self.profiles[s]} for s in SOURCES},
            'counts':self.manifest['counts'],'hashes':self.hashes,
            'results':{s:dict(Counter(r[s]['status'] for r in self.reconciled)) for s in ('crm','omnichannel')} if self.reconciled is not None else None,
            'core_metrics':{'total':len(self.reconciled),
                'reference_both':sum(all(r[s]['status']=='confirmed_by_reference' for s in ('crm','omnichannel')) for r in self.reconciled),
                'review':sum(any(r[s]['status'] in ('candidate','conflict') for s in ('crm','omnichannel')) for r in self.reconciled)} if self.reconciled is not None else None,
            'statuses':STATUSES,'issues':ISSUES}

    def paginate(self,rows,q):
        def number(name,default,maximum):
            value=q.get(name,str(default))
            if not re.fullmatch('[0-9]+',value):raise PanelError('Página/tamanho inválido.')
            number=int(value)
            if not 1<=number<=maximum:raise PanelError('Página/tamanho fora do limite.')
            return number
        size=number('size',25,100);pages=max(1,math.ceil(len(rows)/size));page=min(number('page',1,1000000),pages)
        return {'rows':rows[(page-1)*size:page*size],'total':len(rows),'page':page,'pages':pages,'size':size}

    def dispatch(self,path,query=None):
        q={}
        allowed={'source','search','page','size','issue','status','reveal','id'}
        for k,v in (query or {}).items():
            if k not in allowed or len(v)!=1:raise PanelError('Parâmetro desconhecido/repetido.')
            q[k]=v[0]
        if q.get('reveal','0') not in ('0','1'):raise PanelError('Opção de exibição inválida.')
        reveal=q.get('reveal')=='1';search=q.get('search','').casefold()
        if len(search)>200:raise PanelError('Busca maior que 200 caracteres.')
        if path=='/api/panel/overview':return self.overview()
        if path=='/api/panel/records':
            source=q.get('source','core')
            if source not in SOURCES:raise PanelError('Fonte inválida.')
            rows=self.rows[source]
            if rows is None:raise PanelError('Fonte sintética indisponível; não significa zero registros.',503)
            issue=q.get('issue','all')
            if issue not in ISSUES:raise PanelError('Fila inválida.')
            rows=[self.masked(r,reveal) for r in rows if (issue=='all' or issue in r['issues']) and (not search or search in json.dumps(r,ensure_ascii=False).casefold())]
            return self.paginate(rows,q)
        if path=='/api/panel/reconciliation':
            if self.reconciled is None:return {'available':False,'rows':[], 'total':None,
                'message':'ERP Core indisponível: universo de comparação não definido.'}
            status=q.get('status','all')
            if status!='all' and status not in STATUSES:raise PanelError('Situação inválida.')
            rows=[self.masked(r,reveal) for r in self.reconciled if (status=='all' or any(r[s]['status']==status for s in ('crm','omnichannel'))) and (not search or search in json.dumps(r,ensure_ascii=False).casefold())]
            return {'available':True,**self.paginate(rows,q)}
        if path=='/api/panel/evidence':
            row=next((r for r in self.reconciled or [] if r['id']==q.get('id')),None)
            if row is None:raise PanelError('Cadastro Core não encontrado.',404)
            return self.masked(row,reveal)
        if path=='/api/panel/conversations':
            rows=self.rows['conversations']
            if rows is None:raise PanelError('Omnichannel indisponível; conversas não avaliadas.',503)
            return self.paginate([r for r in rows if not search or search in json.dumps(r).casefold()],q)
        if path=='/api/panel/messages':
            if self.rows['conversations'] is None:raise PanelError('Omnichannel indisponível.',503)
            if not any(r['id']==q.get('id') for r in self.rows['conversations']):raise PanelError('Conversa não encontrada.',404)
            return {'rows':[r for r in self.rows['messages'] if r['conversation_id']==q['id']]}
        raise PanelError('Rota do painel não encontrada.',404)


def make_panel_server(folder='snapshots',port=8790):
    panel=SnapshotPanel(folder);token=secrets.token_urlsafe(32);nonce=secrets.token_urlsafe(24)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def answer(self,status,body,ctype='application/json; charset=utf-8'):
            raw=body if isinstance(body,bytes) else json.dumps(body,ensure_ascii=False,allow_nan=False).encode('utf-8')
            self.send_response(status);self.send_header('Content-Type',ctype)
            self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Content-Security-Policy',f"default-src 'self'; script-src 'self' 'nonce-{nonce}'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if status==405:self.send_header('Allow','GET, HEAD')
            self.end_headers()
            if self.command!='HEAD':self.wfile.write(raw)
        def do_GET(self):
            try:
                port=self.server.server_port;hosts={f'127.0.0.1:{port}',f'localhost:{port}'}
                if self.headers.get('Host') not in hosts:raise PanelError('Host não permitido.',403)
                origin=self.headers.get('Origin')
                if origin and origin not in {'http://'+h for h in hosts}:raise PanelError('Origem não permitida.',403)
                parts=urlsplit(self.path);path=parts.path
                if self.headers.get('Sec-Fetch-Site')=='cross-site' and path.startswith('/api/panel/'):
                    raise PanelError('Requisição externa bloqueada.',403)
                if len(self.path)>8192:raise PanelError('URL muito longa.',414)
                if path=='/health':self.answer(200,{'synthetic':True,'panel_version':'0.3.2','snapshots_loaded':True});return
                if path=='/':
                    html=(WEB/'index.html').read_text(encoding='utf-8')
                    html=html.replace('__BOOTSTRAP__',json.dumps({'token':token,'synthetic':True}).replace('<','\\u003c')).replace('__NONCE__',nonce)
                    self.answer(200,html.encode('utf-8'),'text/html; charset=utf-8');return
                if path in ('/web/app.js','/web/panel.css'):
                    self.answer(200,(WEB/path.rsplit('/',1)[1]).read_bytes(),
                        'application/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8');return
                if not path.startswith('/api/panel/'):raise PanelError('Recurso não encontrado.',404)
                if not hmac.compare_digest(self.headers.get('X-Prisma-Demo-Token',''),token):raise PanelError('Sessão inválida. Recarregue o painel.',403)
                self.answer(200,panel.dispatch(path,parse_qs(parts.query,keep_blank_values=True)))
            except PanelError as exc:self.answer(exc.status,{'error':str(exc),'synthetic':True})
            except Exception:self.answer(500,{'error':'Falha local no painel demo. Nenhum serviço externo foi acessado.','synthetic':True})
        do_HEAD=do_GET
        def write_blocked(self):self.answer(405,{'error':'Painel demo somente leitura.','synthetic':True})
        do_POST=do_PUT=do_PATCH=do_DELETE=do_OPTIONS=write_blocked
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.daemon_threads=True
    return server


def serve_panel(folder='snapshots',port=8790):
    server=make_panel_server(folder,port)
    print(f'Prisma Demo — painel: http://127.0.0.1:{server.server_port} (somente snapshots fictícios). Ctrl+C para parar.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
