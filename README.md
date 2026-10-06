# Prisma Central 0.3.2 — Aurora e Nocturne com vidro

**Fontes distintas. Decisões claras.**

Banco SQLite e APIs locais **inteiramente sintéticos** para demonstrar integração, qualidade e conciliação cadastral entre ERP Core, CRM e Omnichannel.

> Não contém dados de clientes, credenciais, endpoints nem implementação privada da organização. Não é um serviço de produção. O banco é gerado do zero, com seed fixa; nenhum arquivo operacional é lido.

## Estrutura e nome do módulo

Pasta externa: `prisma_central`. Módulo interno: `prisma`. Rode os comandos a partir da pasta externa, ao lado deste README. Não instalar o pacote homônimo Prisma ORM para executar este projeto.

```text
prisma_central/
├── README.md
├── prisma/
│   ├── __init__.py
│   └── __main__.py
├── tests/
├── docs/
└── identidade_prisma/
```

Imports, testes e comandos foram ajustados para `prisma`. O banco mantém o nome técnico `prisma_demo.sqlite` para compatibilidade; não renomear esse arquivo nem regenerar os snapshots por causa desta atualização. Os avisos de dados sintéticos continuam na interface.

## Abrir o painel com os snapshots que você já extraiu

Atualize os arquivos de código da pasta demo com os deste pacote, mantendo `data/`, `snapshots/` e `.venv`. Não copie nada para a instalação operacional. O contrato de geração/API 0.1 foi preservado; seus snapshots existentes são compatíveis se estiverem íntegros e seguirem as convenções sintéticas.

Na pasta que contém este README:

```powershell
python -m prisma panel --snapshots .\snapshots --port 8790
```

Abra **http://127.0.0.1:8790**. A API da porta 8787 não precisa ficar rodando: o painel lê somente a extração local. Encerre o painel com Ctrl+C.

Se ainda não houver snapshots, use o fluxo de geração/API/extração descrito abaixo antes de iniciar o painel. Não há fallback para bases reais ou para diretórios do projeto operacional.

## Ajuste de paleta 0.3.1

Restauradas as cores originais Aurora e Nocturne: fundo claro azulado `#F4F7FC`, escuro azul-marinho `#0E1523` e acentos azuis `#2868D8` / `#88B3FF`. Prisma triangular e glassmorphism preservados. A revisão substitui o prata/grafite excessivamente neutro da 0.3. Sem alteração de dados, API ou regras.

## Revisão visual 0.3

Prisma triangular transparente, superfícies neutras de vidro fosco, reflexos discretos e bordas luminosas. Roxo restrito à assinatura e aos detalhes de seleção; vermelho, azul e verde identificam a origem. O efeito representa transparência das evidências e transformação da leitura multicanal, não fusão automática de pessoas nem conversão comercial medida.

A atualização é de apresentação: geração/API continuam no contrato 0.1.0, snapshots e regras do comparador permanecem compatíveis. Abra `identidade_prisma/Prisma_Identidade_Visual.html` para explorar o guia offline. Detalhes em [Identidade e vidro](docs/IDENTIDADE_VIDRO.md).

## O que esta versão entrega

- Painel Prisma com Resumo, Cadastros, Qualidade, Conciliação, Conversas, Snapshots e Documentação.
- Temas Claro/Escuro/Sistema, navegação lateral, busca, filtros, paginação e detalhes por chave.
- Carregador de snapshots com SHA-256, contagens, IDs/contatos sintéticos e relações de mensagens verificados.
- Gerador determinístico: 120 cadastros Core por padrão, em duas empresas fictícias.
- Três fontes com IDs próprios, campos e envelopes diferentes.
- Dez cenários controlados de qualidade/conciliação; contatos coincidentes não confirmam identidade.
- Conversas e mensagens fictícias com integridade referencial.
- API GET somente leitura e paginação; filtros de empresa e atualização nas rotas aplicáveis.
- Servidor loopback sem dependências e adaptador opcional FastAPI com OpenAPI.
- Extrator que gera snapshots JSONL, manifesto de disponibilidade e hashes.
- Verdade de referência separada do banco/API para testes.
- Testes automatizados e configuração de GitHub Actions.
- Identidade visual Prisma previamente aprovada: guia offline, SVGs e tokens.

**Escopo:** ambiente de demonstração independente. O painel público aplica a identidade Prisma 1.3, com prisma triangular e vidro neutro, mas usa adaptadores próprios para os snapshots da demo e o comparador público simplificado. Não é o backend operacional completo nem uma substituição da instalação interna. Não há importação livre de arquivos, sincronização automática ou escrita entre fontes.

## Executar sem instalar bibliotecas

Requer Python 3.11 ou superior. Descompacte o ZIP e abra o terminal na pasta que contém este README.

```bash
python -m prisma generate --customers 120 --seed 42
python -m prisma check
python -m unittest discover -s tests -v
python -m prisma serve --port 8787
```

Abra no navegador:

```text
http://127.0.0.1:8787/health
http://127.0.0.1:8787/api/demo/meta
http://127.0.0.1:8787/api/demo/core/customers?page=1&page_size=25
http://127.0.0.1:8787/api/demo/crm/contacts?limit=25
http://127.0.0.1:8787/api/demo/omnichannel/customers?limit=25
```

O servidor não usa token e aceita somente loopback `127.0.0.1`. **Não publique este servidor na internet**. Encerre com Ctrl+C.

### Extrair snapshots pela API

Com a API rodando, abra outro terminal na mesma pasta:

```bash
python -m prisma extract --base-url http://127.0.0.1:8787 --out snapshots
```

O extrator percorre todas as páginas das três fontes, conversas e mensagens. Não usa proxies do ambiente, recusa redirecionamentos e não aceita URLs externas. Não sobrescreve extrações existentes: escolha outra pasta para repetir. Uma fonte indisponível não produz um arquivo vazio; sua contagem fica `null` no manifesto.

### FastAPI opcional

Crie um ambiente virtual e instale dependências somente se quiser o adaptador FastAPI:

```bash
python -m venv .venv
```

Ative no PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Ou no Linux/macOS:

```bash
source .venv/bin/activate
```

Então:

```bash
python -m pip install -r requirements-api.txt
python -m prisma serve --engine fastapi --port 8787
```

OpenAPI JSON: `http://127.0.0.1:8787/openapi.json`. Interface Swagger: `http://127.0.0.1:8787/docs` (os assets padrão do Swagger usam CDN; o JSON OpenAPI não depende dela).

O gerador, servidor padrão e testes principais não dependem dessas bibliotecas. FastAPI está incluído como adaptador opcional; sua execução **não foi validada neste ambiente offline**, que não tem as dependências instaladas. O teste opcional será executado quando elas estiverem disponíveis. A configuração de CI foi escrita, mas ainda não executada no GitHub.

## Modelo de dados

```text
companies ───< core_customers

crm_contacts                 # ID nativo próprio + referência Core opcional
omni_customers ───< conversations ───< messages

metadata                     # marcador sintético e manifesto de snapshots
```

A chave de negócio Core é **(company_id, customer_id)**, não apenas o ID local. Há um cenário com o mesmo `customer_id` em duas empresas. CRM e Omnichannel não têm FK rígida para o Core: dados incompletos e referências conflitantes são parte do problema simulado. Todas as referências normais têm a representação `company_id/customer_id`.

Os IDs canônicos de todas as tabelas começam com `DEMO-`. Telefones usam DDD `00`; e-mails usam `example.test`, exceto um valor propositalmente inválido. Documentos são vazios ou `00000000000`, explicitamente inválido. As mensagens declaram seu caráter fictício.

## Cenários de aceitação

| Cenário | Resultado esperado no validador demo |
| --- | --- |
| Referência Core explícita e única | Confirmado pela referência; não é validação civil |
| Contato coincidente sem referência | Candidato, sem fusão |
| Contato compartilhado/duplicado | Conflito |
| Chaves insuficientes | Não comparável |
| Campos inválidos | Não comparável |
| Cadastro somente no Core | Não encontrado no snapshot, com chave utilizável |
| Referência e contatos apontam destinos diferentes | Conflito |
| Referência Core duplicada no destino | Conflito |
| Mesmo ID local em empresas distintas | Referências compostas distintas, confirmação pela referência |
| Contato parcialmente preenchido | Candidato |

Também há registros exclusivos de CRM/Omnichannel, datas de snapshots distintas e simulação de fonte indisponível. A verdade de referência contém a entidade fictícia de origem e o resultado esperado; não é exposta por endpoint nem fornecida ao comparador.

**Importante:** `validation.py` verifica um contrato simplificado de aceitação da demo. Não substitui o motor operacional nem implementa confirmação por documento, máscaras, avaliação completa de comparabilidade temporal, consentimento, score ou tabela mestre. Um `confirmed_by_reference` é apenas o resultado dessa regra, não prova de identidade nem autorização de escrita. Não há fusão ou atualização entre fontes.

## Fonte indisponível

Use uma pasta diferente:

```bash
python -m prisma generate --out data-unavailable --customers 24 --unavailable crm
python -m prisma check --data data-unavailable
python -m prisma serve --data data-unavailable --port 8788
```

A rota CRM retorna HTTP 503. As outras fontes continuam disponíveis. O manifesto informa `available: false`. As contagens do manifesto de geração representam os dados **gerados**, não acesso bem-sucedido à fonte indisponível.

## Reproduzir e regenerar

Mesma seed, quantidade e cenário geram os mesmos conteúdos. Horários de referência são fixos, não o relógio atual. A seed modifica os registros fictícios; não aleatoriza os resultados esperados dos cenários.

Para substituir **somente uma base de demo já identificada**:

```bash
python -m prisma generate --customers 120 --seed 42 --force
```

Pare a API antes de regenerar. A API detecta alterações no manifesto e exige reinício. O gerador se recusa a sobrescrever bancos desconhecidos, mesmo com `--force`.

## Estrutura

```text
prisma/          # Gerador, API, extrator, validador e servidor do painel
  web/               # Apresentação do painel público
identidade_prisma/    # Guia de marca 1.3, vidro e prisma triangular
tests/               # Testes sem dados reais
.github/workflows/   # CI proposta
requirements-api.txt # Dependências opcionais FastAPI
README.md
.gitignore
```

Arquivos de execução em `data/` e `snapshots/` não são versionados: o gerador os recria. Veja [o guia do painel](docs/PAINEL_DEMO.md), [o contrato da API](docs/API.md), [o guia de publicação](docs/PUBLICACAO.md) e [o relatório de validação](docs/VALIDACAO.md).

## Roadmap

1. Ampliar testes e capacidades do comparador público; integração dos snapshots ao painel já entregue na 0.2.
2. Acrescentar extração incremental persistida, checkpoint e simulação de 429/timeout com retry.
3. Ampliar casos de comparabilidade temporal e testes do motor completo.
4. Empacotar com PostgreSQL/Docker se houver necessidade; não é requisito desta versão.

## Publicação e licença

Repositório informado pelo proprietário: https://github.com/kpassaros/prisma-central. Upload ainda pendente de confirmação; nenhuma publicação remota foi executada por esta entrega. Revise os arquivos e direitos de publicação antes do primeiro commit. **A licença ainda deve ser escolhida pelo proprietário**; nenhuma licença permissiva foi presumida. Este pacote não autoriza publicar código da organização nem copiar ativos ou contratos privados.
