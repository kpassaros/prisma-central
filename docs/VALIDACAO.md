# Validação — Prisma Central 0.3.2

## Executado neste ambiente

- Python 3.13, Linux, sem dependências externas para o núcleo da demo.
- 47 testes descobertos: **46 passaram; 1 teste opcional FastAPI foi ignorado** por ausência de FastAPI/httpx.
- Testes de geração determinística, alteração por seed, integridade SQLite/FKs, ID local repetido entre empresas e dez cenários de aceitação.
- Paginação Core e cursores CRM/Omnichannel; rejeição de cursores de outro contexto, parâmetros inválidos e escritas.
- Filtro incremental e normalização de timezone.
- API real em loopback com extração completa, erros HTTP, conversas e mensagens.
- Cenários de fonte indisponível retornando 503 e extração sem arquivo vazio para a fonte indisponível.
- Proteção contra sobrescrita de banco desconhecido, detecção de regeneração e uso de conexão SQLite somente leitura.
- Extrator recusa destinos externos, proxies do ambiente e redirecionamentos.
- Sintaxe Python verificada, inclusive do adaptador FastAPI.

## Painel integrado — validação adicional

- Carregamento dos snapshots do extrator, com hashes e contagens conferidos.
- Rejeição de adulteração, nome/e-mail não sintético, symlink, caminho não permitido e arquivos residuais de fonte indisponível.
- Chave composta empresa/cliente e múltiplos candidatos preservados nas evidências.
- Máscara/revelação, busca, paginação, filtros e histórico de mensagens.
- API do painel com sessão local, Host permitido e escrita bloqueada; nenhuma leitura de .env/banco ou endpoint interno.
- Estados de fontes indisponíveis, inclusive Core sem universo de comparação.
- Indicadores do painel reconciliados por leitura independente dos JSONL e dos resultados esperados da fixture. O painel não lê a verdade de referência.
- Navegador Chromium: 12 estados de rota/tema, filtros, paginação, diálogos, navegação móvel e seletor de tema testados; sem requisições externas nem erros JavaScript.
- Revisão visual de telas desktop e móveis, temas claro/escuro, documentação nas quatro perspectivas e estados de diálogo/consulta vazia.

## Revisão visual 0.3

- SVGs com face frontal triangular; versões para fundos claro e escuro.
- Guia offline 1.3 e painel com superfícies de vidro neutras e roxo restrito a detalhes.
- Temas claro/escuro, desktop 1440px e móvel 390px; documentação das quatro fontes, menus, diálogos e estado vazio revisados visualmente.
- Preferência de movimento reduzido respeitada; alternativas opacas previstas para falta de suporte ao desfoque e transparência reduzida. Não representa auditoria completa de acessibilidade.
- Nenhuma alteração no gerador/API/contrato 0.1.0, nos hashes dos snapshots ou nas regras do comparador.

## Base padrão e extração ponta a ponta

Com seed 42 e 120 cadastros Core:

| Entidade | Quantidade sintética |
| --- | --- |
| Empresas | 2 |
| Clientes Core | 120 |
| Contatos CRM | 119 |
| Clientes Omnichannel | 119 |
| Conversas | 20 |
| Mensagens | 60 |

A extração HTTP percorreu todas as páginas e produziu cinco arquivos JSONL com hashes verificados. São contagens da demo, não da organização.

O validador simplificado encontrou, em cada fonte de destino, 110 confirmações pela referência, 2 candidatos, 5 conflitos, 2 não comparáveis e 1 não encontrado. As duas populações não devem ser somadas como pessoas únicas.

## Não validado / limites

- Execução do adaptador FastAPI/Swagger: dependências ausentes no ambiente offline. Seu teste fica habilitado para ambientes com as bibliotecas instaladas.
- GitHub Actions: configuração fornecida, nenhuma execução no GitHub realizada.
- Núcleo validado aqui em Linux/Python 3.13. O proprietário informou sucesso da geração/API/extração 0.1 no Windows; a revisão visual do painel 0.3 ainda aguarda sua execução nesse ambiente. Conexões são fechadas explicitamente para evitar locks de SQLite.
- Painel público independente integrado aos snapshots da demo. Não foi executada integração com a instalação operacional Prisma 1.2, extratores privados ou APIs reais.
- O validador demo não é o motor operacional completo e não comprova comparabilidade temporal, documentos válidos, identidade civil ou homologação de negócio.
- O servidor é uma ferramenta local de demonstração, não um serviço autenticado, multiusuário ou pronto para produção.
- Não houve pesquisa de disponibilidade de marca, decisão de licença, criação de repositório nem push.

## Ajuste de paleta 0.3.1

Restaurados os tokens originais Aurora/Nocturne. Suíte de 47 testes novamente executada: 46 passaram e 1 opcional FastAPI ignorado. Sete rotas e estados de diálogo/menu/tema em desktop e móvel conferidos, sem erros JavaScript nem chamadas externas. Revisão executada em Linux/Chromium; atualização no Windows ainda precisa ser aplicada pelo proprietário. Backend/contrato de geração/API 0.1.0 e snapshots preservados.

## Renomeação 0.3.2

Raiz `prisma_central`, módulo `prisma`; imports e comandos de instalação/publicação atualizados. 49 testes descobertos: 48 passaram; 1 FastAPI opcional ignorado. Novos testes cobrem `python -m prisma --help`, geração e check pelo novo módulo. Inicialização de `python -m prisma panel` com snapshots existentes e health HTTP confirmados. Frontend e identidade idênticos à 0.3.1; nenhum redesenho nesta atualização. SQLite e contrato sintético 0.1.0 preservados. Windows/GitHub Actions/FastAPI não executados aqui.
