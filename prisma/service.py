"""Contrato público próprio, somente leitura; não replica APIs privadas."""
import base64
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .db import ClosingConnection

class ApiError(Exception):
    def __init__(self,status,code,message):
        super().__init__(message)
        self.status,self.code,self.message=status,code,message
    def payload(self):
        return {'error':{'code':self.code,'message':self.message},'synthetic':True}

class Service:
    def __init__(self,data='data'):
        self.path=(Path(data).resolve()/'prisma_demo.sqlite')
        try:
            with self.connect() as db:
                if db.execute("SELECT value FROM metadata WHERE key='synthetic'").fetchone()[0]!='true':
                    raise ValueError('Banco não sintético.')
                self.manifest=json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
        except (sqlite3.Error,TypeError,ValueError,KeyError) as exc:
            raise ValueError('Gere primeiro uma base Prisma Demo válida; bancos externos não são aceitos.') from exc

    def connect(self):
        db=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True,factory=ClosingConnection)
        db.row_factory=sqlite3.Row
        return db

    def refresh_guard(self):
        with self.connect() as db:
            current=json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
        if current != self.manifest:
            raise ApiError(409,'dataset_changed','Base regenerada. Reinicie a API antes de continuar.')

    def available(self,source):
        if not self.manifest['sources'][source]['available']:
            raise ApiError(503,'source_unavailable','Fonte sintética indisponível; não equivale a zero registros.')

    def metadata(self,source):
        return dict(synthetic=True,source=source,**self.manifest['sources'][source],
            dataset=self.manifest['fingerprint'])

    def integer(self,value,name,low,high):
        if not isinstance(value,str) or not re.fullmatch(r'[0-9]+',value):
            raise ApiError(400,'invalid_parameter',f'{name} deve ser um inteiro.')
        number=int(value)
        if not low<=number<=high:
            raise ApiError(400,'invalid_parameter',f'{name} deve estar entre {low} e {high}.')
        return number

    def since(self,value):
        if not value:
            return None
        try:
            dt=datetime.fromisoformat(value.replace('Z','+00:00'))
            if dt.tzinfo is None or dt.microsecond:
                raise ValueError()
            return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            raise ApiError(400,'invalid_parameter','updated_since exige data/hora ISO-8601 com timezone, sem frações.')

    def query(self,query,allowed):
        for k,v in query.items():
            if k not in allowed or len(v)!=1:
                raise ApiError(400,'invalid_parameter','Parâmetro desconhecido ou repetido.')
        return {k:v[0] for k,v in query.items()}

    def rows(self,table,filters=(),since=None):
        # table e filtros vêm somente de constantes do código, nunca do cliente.
        clauses,params=[],[]
        for col,value in filters:
            clauses.append(f'{col}=?');params.append(value)
        if since:
            clauses.append('updated_at>?');params.append(since)
        where=' WHERE '+' AND '.join(clauses) if clauses else ''
        with self.connect() as db:
            order='created_at,id' if table=='messages' else ('id' if table=='companies' else 'updated_at,id')
            return [dict(r) for r in db.execute(f'SELECT * FROM {table}{where} ORDER BY {order}',params)]

    def cursor(self,path,params,total):
        size=self.integer(params.get('limit','25'),'limit',1,100)
        context=hashlib.sha256(json.dumps({'path':path,'since':params.get('updated_since',''),
            'limit':size,'dataset':self.manifest['fingerprint']},sort_keys=True).encode()).hexdigest()
        offset=0
        if params.get('cursor'):
            try:
                token=params['cursor']
                if len(token)>1024:
                    raise ValueError()
                obj=json.loads(base64.b64decode(token+'='*((-len(token))%4),altchars=b'-_',validate=True))
                offset=obj['offset']
                if obj['context']!=context or type(offset)!=int or not 0<=offset<=total:
                    raise ValueError()
            except (ValueError,KeyError,TypeError,UnicodeDecodeError):
                raise ApiError(400,'invalid_cursor','Cursor inválido ou de outro conjunto de dados/filtro/rota.')
        following=offset+size
        next_cursor=None
        if following<total:
            next_cursor=base64.urlsafe_b64encode(json.dumps({'offset':following,'context':context}).encode()).decode().rstrip('=')
        return offset,size,next_cursor

    def crm(self,row):
        return {'id':row['id'],'properties':{k:row[k] for k in (
            'firstname','lastname','email','phone','core_reference','lifecycle_stage')},'updatedAt':row['updated_at']}

    def omni(self,row):
        return {'id':row['id'],'name':row['name'],'contacts':{'email':row['email'],'phone':row['phone']},
            'customFields':{'core_reference':row['core_reference']},'channel':row['channel'],'updatedAt':row['updated_at']}

    def dispatch(self,path,query=None,method='GET'):
        if method not in ('GET','HEAD'):
            raise ApiError(405,'read_only','A API demo é somente leitura.')
        query=query or {}
        self.refresh_guard()
        if path=='/health':
            self.query(query,set())
            return {'status':'ok','synthetic':True,'version':self.manifest['generator_version']}
        if path=='/api/demo/meta':
            self.query(query,set())
            return self.manifest
        if path=='/api/demo/core/companies':
            self.query(query,set());self.available('core')
            return {'data':self.rows('companies'),'meta':self.metadata('core')}
        if path=='/api/demo/core/customers':
            p=self.query(query,{'page','page_size','company_id','updated_since'});self.available('core')
            page=self.integer(p.get('page','1'),'page',1,1000000)
            size=self.integer(p.get('page_size','25'),'page_size',1,100)
            filters=[('company_id',p['company_id'])] if 'company_id' in p else []
            rows=self.rows('core_customers',filters,self.since(p.get('updated_since')))
            offset=(page-1)*size
            return {'data':rows[offset:offset+size], 'pagination':{'page':page,'page_size':size,
                'total':len(rows),'next_page':page+1 if offset+size<len(rows) else None},'meta':self.metadata('core')}
        if path in ('/api/demo/crm/contacts','/api/demo/omnichannel/customers','/api/demo/omnichannel/conversations'):
            p=self.query(query,{'limit','cursor','updated_since'})
            source='crm' if '/crm/' in path else 'omnichannel'
            self.available(source)
            table='crm_contacts' if source=='crm' else ('conversations' if path.endswith('conversations') else 'omni_customers')
            rows=self.rows(table,since=self.since(p.get('updated_since')))
            offset,size,nxt=self.cursor(path,p,len(rows))
            selected=rows[offset:offset+size]
            if source=='crm':
                result={'results':[self.crm(r) for r in selected],'paging':{'next':{'after':nxt} if nxt else None}}
            else:
                result={'items':[self.omni(r) for r in selected] if table=='omni_customers' else selected,
                    'nextCursor':nxt}
            result['meta']=self.metadata(source)
            return result
        match=re.fullmatch(r'/api/demo/omnichannel/conversations/(DEMO-CONV-[0-9]{5})/messages',path)
        if match:
            p=self.query(query,{'limit','cursor'});self.available('omnichannel')
            with self.connect() as db:
                exists=db.execute('SELECT 1 FROM conversations WHERE id=?',(match[1],)).fetchone()
            if not exists:
                raise ApiError(404,'not_found','Conversa sintética não encontrada.')
            rows=self.rows('messages',[('conversation_id',match[1])])
            offset,size,nxt=self.cursor(path,p,len(rows))
            return {'items':rows[offset:offset+size],'nextCursor':nxt,'meta':self.metadata('omnichannel')}
        raise ApiError(404,'not_found','Rota demo não encontrada.')
