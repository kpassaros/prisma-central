"""Audita a fronteira de publicação do site estático Prisma, sem consultas externas."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from prisma.panel import SnapshotPanel, native, SOURCES, TEXTS

def audit(folder):
    root=Path(folder).resolve()
    expected={'index.html','.nojekyll','.prisma-static-build','build-report.json','assets/app.js','assets/adapter.js','assets/panel.css','data/demo.json',
              *('data/snapshots/'+f for f in ('manifest.json','core.jsonl','crm.jsonl','omnichannel.jsonl','conversations.jsonl','messages.jsonl'))}
    files={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    if files!=expected:raise ValueError('Arquivos fora da fronteira pública: '+str(files^expected))
    if any(p.is_symlink() for p in root.rglob('*')):raise ValueError('Symlink público não permitido.')
    report=json.loads((root/'build-report.json').read_text(encoding='utf-8'))
    if set(report['sha256'])!=expected-{'build-report.json'}:raise ValueError('Inventário de hashes incompleto.')
    for name,digest in report['sha256'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:raise ValueError('Hash público divergente: '+name)
    data=json.loads((root/'data/demo.json').read_text(encoding='utf-8'))
    if data.get('synthetic') is not True or data.get('seed')!=42 or data.get('customers')!=120 or data.get('schema_version')!='1.0':raise ValueError('Contrato de build sintético incompatível.')
    if set(data['scenarios'])!={'normal','crm-off','core-off','omni-off'}:raise ValueError('Cenários incompatíveis.')
    baseline=SnapshotPanel(root/'data/snapshots')
    if baseline.reconciled!=data['scenarios']['normal']['reconciliation']:raise ValueError('Conciliação pública divergente do Python.')
    if baseline.rows!=data['scenarios']['normal']['records']:raise ValueError('Registros públicos divergentes dos snapshots.')
    for key,scenario in data['scenarios'].items():
        unavailable={'normal':None,'crm-off':'crm','core-off':'core','omni-off':'omnichannel'}[key]
        for s in SOURCES:
            available=scenario['overview']['sources'][s]['available']
            if available!=(s!=unavailable):raise ValueError('Disponibilidade incompatível.')
            raw=scenario['raw'][s]
            if not available:
                if raw is not None or scenario['records'][s] is not None or scenario['overview']['counts'][s] is not None:raise ValueError('Fonte ausente convertida em base vazia.')
            else:
                for row in raw:native(row,s)
                if len(raw)!=scenario['overview']['counts'][s]:raise ValueError('Contagem divergente.')
        if unavailable=='core' and scenario['reconciliation'] is not None:raise ValueError('Core ausente com resultado inferido.')
        conv=scenario['records']['conversations'];messages=scenario['records']['messages']
        if conv is not None:
            conv_ids={r['id'] for r in conv};customer_ids={r['id'] for r in scenario['records']['omnichannel']}
            if any(r['customer_id'] not in customer_ids for r in conv):raise ValueError('Conversa sem cliente sintético.')
            if any(r['text'] not in TEXTS or r['conversation_id'] not in conv_ids for r in messages):raise ValueError('Mensagem não sintética ou relação inválida.')
    index=(root/'index.html').read_text(encoding='utf-8')
    app=(root/'assets/app.js').read_text(encoding='utf-8')
    if '__BOOTSTRAP__' in index or '__NONCE__' in index or 'X-Prisma-Demo-Token' in app:raise ValueError('Bootstrap operacional não removido.')
    if 'fetch(' in app:raise ValueError('UI pública contém fetch fora do adaptador de artefato.')
    if 'src="/' in index or 'href="/' in index:raise ValueError('Caminho de asset absoluto incompatível com Pages.')
    return {'files':len(files),'scenarios':4,'synthetic':True,'baseline_python_equivalence':True}

if __name__=='__main__':
    try:print(json.dumps(audit(sys.argv[1] if len(sys.argv)>1 else ROOT/'_site'),ensure_ascii=False))
    except (ValueError,OSError,KeyError) as exc:raise SystemExit('Audit Prisma: '+str(exc))
