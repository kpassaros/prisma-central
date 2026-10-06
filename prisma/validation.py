"""Verificação do contrato público demo — não é o motor operacional completo."""
import json
import re
from collections import defaultdict
from pathlib import Path
from .generator import reference
from .service import Service

def email(value):
    value=value.strip().casefold()
    return value if re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value) else ''

def phone(value):
    value=re.sub(r'\D','',value)
    return value if 10<=len(value)<=15 else ''

def indexes(rows,key):
    result=defaultdict(set)
    for r in rows:
        value=key(r)
        if value:result[value].add(r['id'])
    return result

def prepare(destination,all_core):
    return (indexes(destination,lambda r:r['core_reference']),
        indexes(destination,lambda r:email(r['email'])),
        indexes(destination,lambda r:phone(r['phone'])),
        indexes(all_core,lambda r:email(r['email'])),
        indexes(all_core,lambda r:phone(r['phone'])))

def classify(core,destination,all_core,available=True,prepared=None):
    if not available:return 'not_evaluated'
    refs,emails,phones,core_emails,core_phones=prepared or prepare(destination,all_core)
    e,p=email(core['email']),phone(core['phone'])
    strong=refs.get(reference(core),set())
    contact=emails.get(e,set())|phones.get(p,set())
    if len(strong)>1 or (strong and contact-strong):return 'conflict'
    if strong:return 'confirmed_by_reference'
    if len(contact)>1 or (contact and (len(core_emails.get(e,set()))>1 or len(core_phones.get(p,set()))>1)):
        return 'conflict'
    if contact:return 'candidate'
    return 'not_found' if e or p else 'not_comparable'

def check(data='data'):
    service=Service(data)
    core=service.rows('core_customers');crm=service.rows('crm_contacts');omni=service.rows('omni_customers')
    with service.connect() as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Falha na integridade do banco.')
    for table in ('companies','core_customers','crm_contacts','omni_customers','conversations','messages'):
        for r in service.rows(table):
            if not r['id'].startswith('DEMO-'):raise ValueError('ID sem prefixo sintético.')
            if 'email' in r and r['email'] and r['email']!='EMAIL-DEMO-INVALIDO' and not r['email'].lower().endswith('@example.test'):
                raise ValueError('E-mail fora do domínio reservado.')
            if 'phone' in r and r['phone'] and not r['phone'].startswith('00'):
                raise ValueError('Telefone fora do contrato fictício.')
            if 'document' in r and r['document'] not in ('','00000000000'):
                raise ValueError('Documento fora do contrato fictício.')
    truth=json.loads((Path(data)/'ground_truth.json').read_text(encoding='utf-8'))
    lookup={r['id']:r for r in core};failures=[];totals={'crm':defaultdict(int),'omnichannel':defaultdict(int)}
    prepared={'crm':prepare(crm,core),'omnichannel':prepare(omni,core)}
    for row in truth['rows']:
        for source,rows in (('crm',crm),('omnichannel',omni)):
            availability=service.manifest['sources']['core']['available'] and service.manifest['sources'][source]['available']
            actual=classify(lookup[row['core_id']],rows,core,availability,prepared[source])
            totals[source][actual]+=1
            if actual!=row['expected_'+source]:
                failures.append({'core_id':row['core_id'],'source':source,'expected':row['expected_'+source],'actual':actual})
    result={'synthetic':True,'ok':not failures,'customers':len(core),
        'scenarios':len({r['scenario'] for r in truth['rows']}),
        'results':{s:dict(v) for s,v in totals.items()},'failures':failures,
        'scope':'Validador simplificado do contrato demo; não valida o motor operacional completo.'}
    if failures:raise ValueError(json.dumps(result,ensure_ascii=False))
    return result
