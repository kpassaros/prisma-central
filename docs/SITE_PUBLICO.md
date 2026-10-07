# Prisma Central — site público 0.4.0

## Escopo

Demonstração estática de portfólio, com a identidade Aurora/Nocturne da aplicação local 0.3.2 preservada. O módulo Python não foi renomeado ou exposto à internet. O site inclui as sete áreas existentes e a página Engenharia de Dados.

Os dados são gerados do zero pela demo. Não há cadastro de usuário, banco remoto, importação de arquivo, coleta de formulário, API operacional, credenciais ou conexão com sistemas reais. Cada visitante recebe uma cópia pública da mesma fixture; busca, filtros, máscara, seleção de cenário e etapa são estados individuais em memória. Recarregar ou Restaurar demonstração limpa esses estados. Somente a preferência de tema pode permanecer em localStorage.

O botão de restauração não apaga arquivos nem banco. Nenhum visitante escreve dados nas fontes. Todos os dados publicados, inclusive os temporariamente mascarados na UI, são públicos e sintéticos; máscara não é controle de acesso.

## Fluxo executado no build

1. `generate`: 120 cadastros Core, seed 42, em duas empresas fictícias.
2. `check`: contrato simplificado da demo.
3. API GET em porta efêmera, exclusivamente `127.0.0.1`.
4. `extract`: páginas/cursores e mensagens por conversa; saída JSONL e manifesto.
5. `SnapshotPanel`: SHA-256, contagens, IDs, convenções e relações conferidos.
6. Adaptadores, perfil de qualidade e conciliação pelo Python existente.
7. Exportação de uma allowlist de 14 arquivos estáticos.

O build repete o fluxo para quatro cenários: todas as fontes disponíveis; CRM indisponível; Core indisponível; Omnichannel indisponível. A API é encerrada e o banco temporário é descartado. Fontes indisponíveis mantêm valores null e nenhum arquivo residual.

A base e seus resultados são determinísticos; os metadados de horário do build variam. O JSON público tem cerca de 0.9 MB. Não há loop de geração ou chamadas às APIs Python durante a navegação.

## Engenharia de Dados

Página com sete etapas: Fontes, Extração, Camada bruta, Validação, Tratamento, Conciliação e Consumo. Exemplos de contrato bruto, adaptação, manifesto e evidências vêm do artefato do build. O visitante pode acompanhar cinco cadastros fictícios e trocar o cenário.

Os downloads do manifesto/JSONL referem-se explicitamente à base inicial com todas as fontes. O relatório do build registra inventário e hashes dos arquivos públicos. O site não anuncia API ao vivo, extração em andamento, dados de negócio ou validação de identidade civil.

Retry/checkpoint persistente/retomada são contextualizados como desenho operacional histórico, não recursos implementados no extrator público. Limites de comparação temporal, consentimento, documentos e score são explícitos.

## Arquivos e responsabilidades

- `scripts/build_site.py`: executa o pipeline sintético e cria `_site/`. Recusa sobrescrever um destino desconhecido.
- `scripts/audit_site.py`: confere allowlist, hashes, contratos, relações e equivalência entre os snapshots iniciais e o resultado Python publicado.
- `site/adapter.js`: consultas em memória sobre o JSON público, máscara, busca, filtro e paginação. Não usa endpoints remotos.
- `site/engineering.js`: página integrada ao painel, inserida somente no artefato estático.
- `site/site.css`: extensão responsiva dos estilos aprovados, sem substituir a identidade.
- `tests/test_site.py`: contratos do build e fronteira de publicação.
- `.github/workflows/pages.yml`: testes, build, auditoria e publicação Pages somente na main. PR executa build mas não deploy.
- `.gitignore`: exclui `_site/`; artefatos são gerados, não versionados.

`prisma/web/*` permanece intacto. O build lê esses arquivos e modifica exclusivamente as cópias de saída. Arquivos completos dos novos módulos estão no pacote, não trechos para montagem manual.

## Prévia local

Requer Python 3.11+; não precisa Node/npm ou bibliotecas externas para o build.

```bash
python -m unittest discover -s tests -v
python scripts/build_site.py
python scripts/audit_site.py _site
python -m http.server 8000 --directory _site --bind 127.0.0.1
```

Abra `http://127.0.0.1:8000/`. Engenharia: `http://127.0.0.1:8000/#Engenharia%20de%20Dados`. Não abrir `index.html` por duplo clique: o navegador precisa servir o JSON por HTTP. Encerre com Ctrl+C.

O servidor da prévia também permanece local. A publicação envia apenas o conteúdo `_site/`, não esse servidor Python.

## Publicação manual no GitHub

1. Preservar a versão atual com uma tag de rollback ou ZIP.
2. Branch `feat/site-publico` a partir da main; aplicar apenas os arquivos do pacote de alterações na raiz.
3. Commit completo: `feat: publica demo estática sintética e jornada de engenharia de dados`.
4. Abrir Pull Request para main e conferir os checks existentes e o job `build` de `Prisma Central Pages`.
5. Aprovar a prévia antes do merge.
6. Em Settings → Pages, selecionar Source: GitHub Actions. Não habilitar um servidor Python público nem publicar a raiz do repositório como artefato.
7. Merge somente com checks verdes e prévia aprovada. Deploy é condicionado à main; também há workflow_dispatch.
8. Verificar o URL retornado pelo job de deploy. Destino esperado para este repositório: `https://kpassaros.github.io/prisma-central/`, ainda não comprovado publicado por esta entrega.
9. Conferir navegação, temas, casos de fonte ausente, modal, downloads, celular e restauração no endereço público. Manter a branch até homologação.

Custos, políticas e disponibilidade do GitHub Pages dependem da conta e da configuração atual. Não foram consultados remotamente. As referências de actions seguem o formato de workflow preparado; execução remota e publicação precisam ser confirmadas pelos logs do proprietário.

## Validação local desta entrega

Linux/Python 3.13: 60 testes executados, 59 aprovados e 1 FastAPI opcional ignorado por dependências ausentes. O build real executou quatro cenários e a auditoria conferiu 14 arquivos permitidos; baseline publicado comparado com o motor Python. Não houve alteração da aplicação local.

A revisão no navegador é registrada junto à entrega; não substitui execução no GitHub ou homologação pública. Windows, FastAPI e actions remotas não foram executados nesta entrega.

## Rollback

Antes do merge, basta fechar o PR sem alterar a main. Depois, reverter o commit/merge que adicionou o site e restaurar os arquivos modificados da versão estável. Se for preciso retirar imediatamente o site, despublicar via Settings → Pages; confirmar o estado público após a ação. Reverter arquivos e despublicar são ações diferentes.

`SHA256SUMS.txt` é atualizado para a árvore-fonte da entrega, excluindo `_site/`, caches e o próprio manifesto. Não equivale aos hashes dos snapshots nem a uma assinatura de autenticidade. Os hashes públicos gerados ficam em `_site/build-report.json`.


## Favicon — correção incremental

O build público copia `site/favicon.svg` e `site/favicon.ico` para a raiz do
artefato e insere referências relativas no HTML gerado. Não editar `_site`
manualmente: o próximo build o recria. Nenhuma mudança na aplicação Python local.

O SVG reutiliza integralmente a geometria e as cores de entrada do símbolo
aprovado em `identidade_prisma/prisma-symbol.svg`. O contorno acompanha a
preferência claro/escuro do navegador por `prefers-color-scheme`; isso não depende
do seletor Aurora/Nocturne da página. O ICO contém 16, 32 e 48 pixels, com contorno
Aurora e transparência, para navegadores sem suporte ao SVG. Sem fontes externas,
JavaScript extra, manifest de PWA ou alteração da identidade visual.

A query `?v=1` permite versionar referências dos ícones. Ao mudar os ícones,
atualize a versão das referências e os testes correspondentes. Navegadores
podem manter cache de favicon; após o deploy, confirmar também em janela anônima.

Checks: `python -m unittest discover -s tests -v`,
`python scripts/build_site.py`, `python scripts/audit_site.py _site`.
A allowlist e os hashes incluem os dois ícones. O workflow existente permanece
inalterado: PR executa build/testes; deploy somente na main.
