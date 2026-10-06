# Painel Prisma Central 0.3.2

## Atualizar a demo 0.1 ou 0.2

1. Pare os processos demo antes de atualizar o código.
2. Faça uma cópia de segurança da pasta `prisma_central`.
3. Copie os arquivos deste ZIP para essa mesma pasta demo. Preserve `data/`, `snapshots/`, `.venv` e extrações anteriores; o pacote não contém esses diretórios.
4. Na pasta que contém `README.md`, execute:

```powershell
python -m prisma panel --snapshots .\snapshots --port 8790
```

5. Abra `http://127.0.0.1:8790`. Use Ctrl+F5 se o navegador exibir código antigo.

Não executar o comando dentro da pasta `prisma` (módulo). Não substituir arquivos da instalação operacional nem mover bases reais para esta demo. O painel exige snapshots do extrator público 0.1.

## Separação do ambiente interno

- Não aceita parâmetro `--projeto`, credenciais ou endpoints externos.
- Não lê `.env`, mapeamentos operacionais, módulos privados ou banco interno.
- Lê somente `manifest.json` e os cinco nomes de arquivos JSONL permitidos na pasta especificada.
- Não procura dados automaticamente no diretório pai.
- O SQLite gerado e a API da porta 8787 não são necessários para abrir uma extração já existente.
- O painel usa a porta 8790 em loopback; não há opção para expô-lo em 0.0.0.0.
- A API do painel tem token de sessão local, validação de Host/origem e CSP. Isso não constitui autenticação multiusuário nem homologação de segurança para internet.

## Validação da extração

O manifesto exige `synthetic: true`, dataset em formato de hash, três fontes, contagens e SHA-256 de cada arquivo disponível. Arquivos desconhecidos na lista de hashes, symlinks, contagem divergente e arquivos adulterados são recusados. Campos/nomes devem seguir o contrato estrito do gerador 0.1: IDs DEMO, nomes fictícios definidos, domínio example.test, DDD 00 e documentos vazios/explicitamente inválidos. Relações de conversas e mensagens são verificadas.

O marcador e os hashes, isoladamente, **não provam origem sintética**. Não adaptar o carregador para aceitar dados operacionais. Se o gerador evoluir, versionar o contrato e atualizar seus testes antes de relaxar as validações.

Uma fonte indisponível tem contagem null e não deve ter arquivo residual. Use uma pasta nova a cada extração para não misturar versões. O painel carrega uma cópia imutável na inicialização: reinicie para trocar a extração. “Tentar novamente” recarrega a tela, não importa arquivos nem refaz a extração.

## Telas

- **Resumo:** universo Core, confirmação por referência em ambos os destinos, necessidade de revisão e resultados separados por fonte.
- **Cadastros:** fonte fictícia selecionável, busca, filas de qualidade, paginação e máscara opcional.
- **Qualidade dos dados:** preenchimento, sintaxe de e-mail, contatos compartilhados e documentos não modelados/ausentes/inválidos. Filas se sobrepõem.
- **Conciliação:** Core como referência, estados CRM/Omnichannel e ficha de evidências com múltiplos candidatos e ocorrências de cada chave.
- **Conversas:** histórico fictício com mensagens de cliente, atendente e sistema.
- **Snapshots:** disponibilidade, datas da extração e hashes verificados.
- **Documentação e regras:** quatro perspectivas — Omnichannel vermelho, CRM azul, ERP Core verde e Prisma roxo.

As tabelas largas rolam dentro de sua região em telas pequenas. O modo padrão mascara nomes e contatos, mesmo sendo fictícios; marcar “Mostrar os dados fictícios sem máscara” é uma demonstração de controle de visualização, não autorização de acesso a dados reais.

## Limites do comparador

É o comparador público simplificado da demo, com evidências calculadas a partir dos próprios snapshots. Não lê ground_truth.json nem recebe a resposta esperada dos testes. Não é o motor operacional completo, não confirma CPF, não faz fusão e não escreve no CRM.

“Pela referência” descreve a regra no snapshot; não prova identidade civil, titularidade, consentimento ou presença atual. Os horários das fontes diferem. O painel explicita essa diferença, mas não implementa todas as políticas de comparabilidade temporal do produto futuro. Não há score global ou soma de fontes como pessoas únicas.

## Problemas comuns

- **Snapshot obrigatório ausente:** execute o extrator para uma pasta nova, ou confirme `--snapshots`.
- **SHA-256 divergente:** não corrija o hash manualmente para esconder uma mudança. Faça uma nova extração sintética coerente.
- **Fonte indisponível com arquivo residual:** use outra pasta de extração, sem os arquivos anteriores.
- **Porta ocupada:** encerre o outro painel ou escolha `--port 8791` e use a nova URL.
- **Sessão inválida:** recarregue o navegador. A sessão muda ao reiniciar o servidor.
- **Contrato não sintético:** o painel recusa os arquivos. Não use snapshots operacionais.
- **API desligada:** isso é normal se os snapshots já existem; o painel é offline.

## Contratos do painel

Todas as rotas estão sob `/api/panel/`, são GET e exigem o token da sessão entregue à página.

`overview`, `records`, `reconciliation`, `evidence`, `conversations` e `messages` são os recursos permitidos. Fonte/status/fila/página/tamanho são validados e resultados são paginados. Não há endpoints de importar, sincronizar, exportar dados reais ou escrever entre sistemas. Arquivos estáticos só são servidos por nomes permitidos.

## Revisão visual 0.3

Prisma triangular, vidro neutro claro/escuro, roxo somente como detalhe. Menu, cartões, controles e diálogos compartilham superfícies translúcidas com desfoque e bordas luminosas; leitura e evidências preservadas. Há alternativas opacas para navegadores sem suporte e preferência de transparência reduzida. Nenhuma alteração de banco, API, snapshots ou regras de conciliação. Veja `IDENTIDADE_VIDRO.md`.

## Paleta 0.3.1

Aurora e Nocturne originais restaurados; fundo azul-marinho no escuro e azul suave no claro. Mantidos prisma triangular e vidro. A opção de tema continua Claro/Escuro/Sistema. Atualização somente visual, compatível com snapshots existentes.

## Nomes 0.3.2

Raiz externa: `prisma_central`. Módulo interno: `prisma`. Rodar `python -m prisma` da raiz externa. Após backup, substitua o código pelo pacote novo e preserve `data/`, `snapshots/` e `.venv`. Retire a pasta antiga `prisma_demo` da árvore pública após conferir a nova instalação; ela não é usada pelo novo comando. Não renomear o banco técnico `prisma_demo.sqlite`.
