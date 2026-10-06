"""Geração determinística. Não lê arquivos, APIs ou variáveis da organização."""
import csv
import hashlib
import json
import random
import sqlite3
from pathlib import Path
from .db import ClosingConnection

VERSION = '0.1.0'
TIMES = {'core': '2026-01-15T12:00:00Z', 'crm': '2026-01-15T12:00:00Z', 'omnichannel': '2026-01-15T11:00:00Z'}
SCHEMA = '''
PRAGMA foreign_keys = ON;
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE companies (id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE core_customers (
 id TEXT PRIMARY KEY, company_id TEXT NOT NULL REFERENCES companies(id),
 customer_id TEXT NOT NULL, name TEXT NOT NULL, email TEXT NOT NULL,
 phone TEXT NOT NULL, document TEXT NOT NULL, city TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(company_id, customer_id));
CREATE TABLE crm_contacts (
 id TEXT PRIMARY KEY, firstname TEXT NOT NULL, lastname TEXT NOT NULL,
 email TEXT NOT NULL, phone TEXT NOT NULL, core_reference TEXT NOT NULL,
 lifecycle_stage TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE omni_customers (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL,
 core_reference TEXT NOT NULL, channel TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE conversations (
 id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES omni_customers(id),
 status TEXT NOT NULL, channel TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE messages (
 id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id),
 sender TEXT NOT NULL CHECK(sender IN ('customer','agent','system')),
 text TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX idx_core_time ON core_customers(updated_at,id);
CREATE INDEX idx_crm_time ON crm_contacts(updated_at,id);
CREATE INDEX idx_omni_time ON omni_customers(updated_at,id);
CREATE INDEX idx_messages ON messages(conversation_id,created_at,id);
'''

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def reference(row):
    return row['company_id'] + '/' + row['customer_id']

def is_demo_db(path):
    if not path.exists():
        return False
    try:
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, factory=ClosingConnection) as db:
            return db.execute("SELECT value FROM metadata WHERE key='synthetic'").fetchone() == ('true',)
    except sqlite3.Error:
        return False

def generate(out='data', customers=120, seed=42, unavailable='none', force=False):
    if not 24 <= customers <= 100000:
        raise ValueError('customers deve estar entre 24 e 100000.')
    if unavailable not in ('none','core','crm','omnichannel'):
        raise ValueError('Fonte indisponível inválida.')
    out = Path(out).resolve()
    db_path = out / 'prisma_demo.sqlite'
    # Nunca sobrescrever um banco desconhecido. Regeração exige autorização explícita.
    if db_path.exists() and (not force or not is_demo_db(db_path)):
        raise ValueError('Banco já existe: --force só substitui um banco marcado como Prisma Demo.')
    out.mkdir(parents=True, exist_ok=True)
    staging = out / '.prisma_demo.generating.sqlite'
    if staging.exists():
        raise ValueError('Há uma geração interrompida. Remova somente o arquivo temporário de demo e tente novamente.')
    rng = random.Random(seed)
    names = ['Pessoa Aurora','Pessoa Horizonte','Pessoa Cristal','Pessoa Violeta','Pessoa Solar','Pessoa Lume']
    core = []
    scenarios = {}
    for i in range(customers):
        company = 'DEMO-COMP-A' if i % 2 == 0 else 'DEMO-COMP-B'
        local_id = f'DEMO-LOCAL-{i+1:05d}'
        if i in (10,11):
            local_id = 'DEMO-LOCAL-COMMON'  # Mesmo ID local em empresas distintas.
        core.append(dict(id=f'DEMO-CORE-{i+1:05d}', company_id=company, customer_id=local_id,
            name=f'{rng.choice(names)} {i+1:05d}', email=f'pessoa.{i+1:05d}@example.test',
            phone=f'00{rng.randrange(100000000, 999999999):09d}', document='',
            city=f'Cidade Fictícia {rng.randrange(1,7)}', updated_at='2026-01-14T10:00:00Z'))
        scenarios[i] = 'explicit_reference'
    scenarios.update({0:'explicit_reference',1:'contact_only',2:'shared_contact',3:'shared_contact',
        4:'insufficient_keys',5:'invalid_fields',6:'core_only',7:'conflicting_evidence',
        8:'conflicting_evidence',9:'duplicate_reference',10:'company_scoped_id',11:'company_scoped_id',
        12:'partial_contact'})
    core[3]['email'] = core[2]['email']
    core[3]['phone'] = core[2]['phone']
    core[4].update(email='', phone='', document='')
    core[5].update(email='EMAIL-DEMO-INVALIDO', phone='', document='00000000000')
    core[12]['email'] = ''
    core[0]['updated_at'] = '2026-01-15T09:00:00Z'
    crm, omni, truths = [], [], []
    for i,row in enumerate(core):
        case = scenarios[i]
        refs = reference(row) if case in ('explicit_reference','company_scoped_id','conflicting_evidence','duplicate_reference') else ''
        email, phone = row['email'], row['phone']
        if case == 'conflicting_evidence':
            other = core[8 if i == 7 else 7]
            email,phone = other['email'],other['phone']
        if i not in (4,5,6):
            crm.append(dict(id=f'DEMO-CRM-{i+1:05d}', firstname=row['name'], lastname='Sintética',
                email=email.upper() if case == 'contact_only' else email, phone=phone,
                core_reference=refs, lifecycle_stage=rng.choice(['lead','qualified','customer']),
                updated_at=row['updated_at']))
            omni.append(dict(id=f'DEMO-OMNI-{i+1:05d}', name=row['name'], email=email, phone=phone,
                core_reference=refs, channel=rng.choice(['chat-demo','messenger-demo']),
                updated_at='2026-01-14T10:00:00Z'))
        status = {'explicit_reference':'confirmed_by_reference','company_scoped_id':'confirmed_by_reference',
            'contact_only':'candidate','partial_contact':'candidate','shared_contact':'conflict',
            'conflicting_evidence':'conflict','duplicate_reference':'conflict',
            'insufficient_keys':'not_comparable','invalid_fields':'not_comparable','core_only':'not_found'}[case]
        truths.append(dict(core_id=row['id'], scenario=case, expected_crm=status,
            expected_omnichannel=status, latent_entity=f'DEMO-ENTITY-{i+1:05d}'))
    # Referência duplicada: os dois candidatos são preservados, sem escolher um.
    for rows,prefix in ((crm,'CRM'),(omni,'OMNI')):
        dup = next(dict(r) for r in rows if r['id'].endswith('00010'))
        dup['id'] = f'DEMO-{prefix}-DUPLICATE-REF'
        rows.append(dup)
        if prefix == 'CRM':
            rows.append(dict(id='DEMO-CRM-ONLY',firstname='Pessoa Exclusiva Demo',lastname='Sintética',
                email='crm.only@example.test',phone='',core_reference='',lifecycle_stage='lead',
                updated_at='2026-01-15T10:00:00Z'))
        else:
            rows.append(dict(id='DEMO-OMNI-ONLY',name='Pessoa Exclusiva Demo',email='omni.only@example.test',
                phone='',core_reference='',channel='chat-demo',updated_at='2026-01-14T10:00:00Z'))
    conversations,messages = [],[]
    for i,row in enumerate(omni[:min(20,len(omni))]):
        cid=f'DEMO-CONV-{i+1:05d}'
        conversations.append(dict(id=cid,customer_id=row['id'],status='closed' if i%2==0 else 'open',
            channel=row['channel'],created_at='2026-01-14T10:00:00Z',updated_at='2026-01-14T10:05:00Z'))
        for j,(sender,text) in enumerate([('customer','Olá! Esta mensagem é inteiramente fictícia.'),
            ('agent','Atendimento simulado do Prisma Demo. Nenhum cliente real.'),
            ('system','Cenário de portfólio: evento sintético de encaminhamento.')]):
            messages.append(dict(id=f'DEMO-MSG-{i+1:05d}-{j+1}',conversation_id=cid,
                sender=sender,text=text,created_at=f'2026-01-14T10:0{j}:00Z'))
    for truth in truths:
        if unavailable == 'core':
            truth['expected_crm']=truth['expected_omnichannel']='not_evaluated'
        elif unavailable != 'none':
            truth['expected_'+unavailable]='not_evaluated'
    datasets={'core_customers':core,'crm_contacts':crm,'omni_customers':omni,
        'conversations':conversations,'messages':messages}
    fingerprint=hashlib.sha256(json.dumps(datasets,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    manifest=dict(synthetic=True, generator_version=VERSION, seed=seed, fingerprint=fingerprint,
        companies=2, counts={k:len(v) for k,v in datasets.items()},
        sources={s:dict(available=s!=unavailable,snapshot_at=TIMES[s]) for s in TIMES})
    try:
        with sqlite3.connect(staging, factory=ClosingConnection) as db:
            db.executescript(SCHEMA)
            db.executemany('INSERT INTO companies VALUES (?,?)',[
                ('DEMO-COMP-A','Empresa Fictícia Aurora'),('DEMO-COMP-B','Empresa Fictícia Horizonte')])
            db.executemany('INSERT INTO metadata VALUES (?,?)',[
                ('synthetic','true'),('manifest',json.dumps(manifest,sort_keys=True)),('version',VERSION)])
            for table,rows in datasets.items():
                keys=list(rows[0])
                sql=f"INSERT INTO {table} ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})"
                db.executemany(sql,[tuple(r[k] for k in keys) for r in rows])
            if db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Falha de integridade relacional.')
        staging.replace(db_path)
    except Exception:
        staging.unlink(missing_ok=True)
        raise
    dump(out/'manifest.json',manifest)
    # A verdade de referência não é armazenada no banco nem exposta na API.
    lineage={}
    for prefix,rows in (('CRM',crm),('OMNI',omni)):
        for r in rows:
            if r['id'].endswith('DUPLICATE-REF'):
                entity='DEMO-ENTITY-00010'
            elif r['id'].endswith('ONLY'):
                entity=f'DEMO-ENTITY-{prefix}-ONLY'
            else:
                entity='DEMO-ENTITY-'+r['id'].rsplit('-',1)[1]
            lineage[r['id']]=entity
    dump(out/'ground_truth.json',dict(synthetic=True,seed=seed,rows=truths,source_entities=lineage))
    return manifest
