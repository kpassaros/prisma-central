"""Constrói uma demo pública SOMENTE a partir do gerador sintético local.
Não importa snapshots, credenciais ou bases externas. Python 3.11+.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prisma.generator import generate
from prisma.validation import check
from prisma.http_server import make_server
from prisma.extractor import extract
from prisma.panel import SnapshotPanel

SCENARIOS = {'normal': 'none', 'crm-off': 'crm', 'core-off': 'core', 'omni-off': 'omnichannel'}
MARKER = '.prisma-static-build'

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n', encoding='utf-8')

def prepare_scenario(work, key, unavailable, published):
    data, snapshots = work / key / 'database', work / key / 'snapshots'
    generate(str(data), 120, 42, unavailable, False)
    check(str(data))
    server = make_server(str(data), 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        extract('http://127.0.0.1:' + str(server.server_port), str(snapshots))
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
    panel = SnapshotPanel(snapshots)
    # Momento do carregamento é metadado do build, não relógio vivo do site.
    panel.loaded_at = datetime.now(timezone.utc).isoformat()
    overview = panel.overview()
    if key == 'normal':
        published.mkdir(parents=True, exist_ok=True)
        for name in ('manifest.json', *panel.hashes):
            shutil.copyfile(snapshots / name, published / name)
    return {'overview': overview, 'records': panel.rows, 'reconciliation': panel.reconciled,
            'raw': {s: panel.raw[s] for s in ('core', 'crm', 'omnichannel')},
            'manifest': panel.manifest}

def build(output):
    output = Path(output).resolve()
    if output == ROOT or output in ROOT.parents or output.parent == output:
        raise ValueError('Destino de build não pode ser a raiz do projeto/sistema.')
    if output.exists() and (output.is_symlink() or not output.is_dir() or not (output / MARKER).is_file()):
        raise ValueError('Destino existente não identificado como build Prisma. Escolha uma pasta nova.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='prisma-synthetic-') as temp:
        work = Path(temp)
        staged = work / 'public'; (staged / 'assets').mkdir(parents=True)
        bundle = {'synthetic': True, 'schema_version': '1.0', 'site_version': '0.4.0',
                  'generator_version': '0.3.2', 'seed': 42, 'customers': 120,
                  'generated_at': datetime.now(timezone.utc).isoformat(), 'scenarios': {}}
        for key, unavailable in SCENARIOS.items():
            bundle['scenarios'][key] = prepare_scenario(work, key, unavailable, staged / 'data' / 'snapshots')
        write_json(staged / 'data' / 'demo.json', bundle)
        # O contrato da UI local é preservado; só o artefato estático recebe adaptações.
        app = (ROOT / 'prisma/web/app.js').read_text(encoding='utf-8')
        old_api = app[app.index('async function api(path)'):app.index('\nfunction toast')]
        app = app.replace(old_api, 'async function api(path){return window.PrismaStatic.api(path)}')
        app = app.replace("const BOOT=window.PRISMA_DEMO_BOOT;delete window.PRISMA_DEMO_BOOT;", '')
        app = app.replace("let preference='escuro'", "let preference='sistema'")
        app = app.replace("const pages=[", "const pages=[['Engenharia de Dados','network'],")
        app = app.replace("collapsed:true", "collapsed:false")
        app = app.replace("'Documentação e regras':docsPage", "'Documentação e regras':docsPage,'Engenharia de Dados':engineeringPage")
        app = app.replace("+body()+'<footer", "+window.PrismaStatic.controls()+body()+'<footer")
        app = app.replace('Prisma Demo 0.3.1', 'Prisma Central · Site demo 0.4.0')
        app = app.replace('Demo · somente leitura', 'Demo · dados sintéticos')
        app = app.replace('Snapshots fictícios', 'Dados sintéticos')
        app = app.replace('Demo · somente leitura', 'Demo · dados sintéticos')
        app = app.replace('Carregando os snapshots fictícios verificados. Nenhum serviço da organização é acessado.',
                          'Carregando o artefato público sintético. Nenhuma API operacional é acessada.')
        app = app.replace('Este painel lê somente os snapshots extraídos, com SHA-256 verificado. Não consulta a organização.',
                          'Este site consulta resultados sintéticos preparados e verificados no build. Não executa uma API ou banco remoto.')
        app = app.replace('O painel não faz sincronização automática.', 'O site consulta resultados previamente preparados; não faz sincronização automática.')
        app = app.replace('Carregado em ', 'Validado no build em ')
        app = app.replace('Leitura imutável desta extração. Para usar outra extração, pare o painel e reinicie com --snapshots apontando para a pasta nova.',
                          'Cópia sintética previamente preparada. Os cenários alternativos são outras execuções sintéticas; nenhuma fonte real é desligada.')
        app = app.replace('O painel (porta 8790) funciona offline depois que os snapshots existem. Não há dependência do projeto operacional.',
                          'O painel local (porta 8790) lê os snapshots. Este site estático apresenta seus resultados preparados; não executa a API Python. Não há dependência operacional.')
        app = app.replace("S.page=page;S.pageNumber", "S.page=page;history.replaceState(null,'','#'+encodeURIComponent(page));S.pageNumber")
        # Página de engenharia usa as mesmas funções de componentes, escape e modal.
        engineering = (ROOT / 'site/engineering.js').read_text(encoding='utf-8')
        hook = "document.addEventListener('click',e=>{const control=e.target.closest('[data-action]');"
        if hook not in app: raise ValueError('Contrato da UI mudou; revisar integração estática.')
        app = app.replace(hook, engineering + '\n' + hook)
        app = app.replace("if(action==='page')navigate(value);", "if(action==='pipeline-stage'){window.PrismaStatic.stage=Number(value);render()}else if(action==='trace-evidence'){S.reveal=true;evidence(window.PrismaStatic.traceId)}else if(action==='restore-demo'){window.PrismaStatic.reset();S.pageNumber=1;S.search='';S.issue='all';S.status='all';S.source='core';S.reveal=false;$('#dialog').close();hydrate();toast('Demonstração restaurada. Nenhum dado remoto foi alterado.')}else if(action==='page')navigate(value);")
        app = app.replace("if(e.target.id==='source-select')", "if(e.target.id==='scenario-select'){window.PrismaStatic.scenario=e.target.value;S.pageNumber=1;S.search='';S.issue='all';S.status='all';$('#dialog').close();hydrate()}else if(e.target.id==='trace-select'){window.PrismaStatic.traceId=e.target.value;render()}else if(e.target.id==='source-select')")
        # Substitui apenas o conteúdo da ajuda da UI pública, sem mexer na ajuda local.
        a = app.index("else if(action==='help')showDialog(")
        b = app.index("});\ndocument.addEventListener('change'", a)
        app = app[:a] + "else if(action==='help')showDialog('Como funciona esta demonstração',notice('SITE ESTÁTICO · Todos os arquivos publicados são sintéticos. Não há API Python ou banco remoto neste site.')+'<p class=\"demo-contract\">O pipeline Python gerou e validou as bases e snapshots durante o build. Busca, filtros e navegação são executados no navegador sobre o artefato JSON. Máscaras são recurso visual, não proteção de dados públicos.</p><p class=\"demo-contract\">Cada visitante tem um estado de navegação em memória, descartado ao recarregar. A preferência de tema pode permanecer no navegador. Cenários de indisponibilidade são preparados, não incidentes ao vivo. Nenhuma informação enviada pelo visitante é coletada.</p><p class=\"demo-contract\">O comparador é simplificado: contato não comprova identidade, consentimento ou autorização de escrita. As cópias têm horários diferentes.</p>')" + app[b:]
        app = app.replace("applyTheme(preference);hydrate();", "try{const route=decodeURIComponent(location.hash.slice(1));if(pages.some(p=>p[0]===route))S.page=route;else if(!qp.get('pagina'))S.page='Resumo'}catch{}\nwindow.addEventListener('hashchange',()=>{try{navigate(decodeURIComponent(location.hash.slice(1)))}catch{}});\napplyTheme(preference);hydrate();")
        (staged / 'assets/app.js').write_text(app, encoding='utf-8')
        css = (ROOT / 'prisma/web/panel.css').read_text(encoding='utf-8') + '\n' + (ROOT / 'site/site.css').read_text(encoding='utf-8')
        (staged / 'assets/panel.css').write_text(css, encoding='utf-8')
        shutil.copyfile(ROOT / 'site/adapter.js', staged / 'assets/adapter.js')
        # Ícones locais: SVG adaptativo e ICO de compatibilidade, sem mudar a UI Python.
        for name in ('favicon.svg', 'favicon.ico'):
            shutil.copyfile(ROOT / 'site' / name, staged / name)
        html = (ROOT / 'prisma/web/index.html').read_text(encoding='utf-8')
        html = html.replace('/web/panel.css', './assets/panel.css').replace('/web/app.js', './assets/app.js')
        html = html.replace('<title>Prisma Demo — conciliação sintética</title>', '<title>Prisma Central — Engenharia de Dados e Conciliação</title><meta name="description" content="Explore qualidade e conciliação entre três fontes fictícias e acompanhe o pipeline de engenharia de dados. Portfólio de Kaíque Passaros."><meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="default-src \'self\'; script-src \'self\'; style-src \'self\' \'unsafe-inline\'; img-src \'self\' data:; connect-src \'self\'; object-src \'none\'; base-uri \'self\'; form-action \'none\'">')
        html = html.replace('<script nonce="__NONCE__">window.PRISMA_DEMO_BOOT=__BOOTSTRAP__;</script>', '<script src="./assets/adapter.js" defer></script>')
        html = html.replace('</head>', '<link rel="icon" href="./favicon.ico?v=1" sizes="16x16 32x32 48x48" type="image/x-icon"><link rel="icon" href="./favicon.svg?v=1" sizes="any" type="image/svg+xml"></head>')
        (staged / 'index.html').write_text(html, encoding='utf-8')
        (staged / '.nojekyll').write_text('')
        (staged / MARKER).write_text('Prisma static build v1\n')
        asset_hashes = {str(p.relative_to(staged)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(staged.rglob('*')) if p.is_file()}
        report = {'synthetic': True, 'seed': 42, 'customers': 120, 'scenarios': list(SCENARIOS),
                  'pipeline': ['generate', 'check', 'HTTP loopback extract', 'SnapshotPanel validation', 'reconcile', 'static export'],
                  'sha256': asset_hashes, 'external_requests': False}
        write_json(staged / 'build-report.json', report)
        allowed = {'.nojekyll', MARKER, 'favicon.svg', 'favicon.ico', 'index.html', 'build-report.json', 'assets/app.js', 'assets/adapter.js', 'assets/panel.css', 'data/demo.json',
                   *('data/snapshots/' + f for f in ('manifest.json','core.jsonl','crm.jsonl','omnichannel.jsonl','conversations.jsonl','messages.jsonl'))}
        actual = {str(p.relative_to(staged)) for p in staged.rglob('*') if p.is_file()}
        if actual != allowed: raise ValueError('Arquivos fora da allowlist pública: ' + str(actual ^ allowed))
        if output.exists(): shutil.rmtree(output)  # Somente destino identificado pelo marcador acima.
        shutil.copytree(staged, output)
        return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default=str(ROOT / '_site'))
    args = parser.parse_args()
    try:
        result = build(args.out)
        print('Site estático pronto: ' + str(Path(args.out).resolve()))
        print('4 cenários; seed 42; 120 cadastros Core; somente artefatos sintéticos na saída.')
    except (ValueError, OSError) as exc:
        parser.exit(1, 'Build Prisma: ' + str(exc) + '\n')
