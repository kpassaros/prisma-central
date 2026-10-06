# Publicar o Prisma Demo no GitHub

Este pacote é um projeto demo independente com painel público integrado aos snapshots. Mantém a identidade Prisma, mas não é o backend completo da organização nem uma distribuição da instalação operacional 1.2. Repositório, remoto e push ainda não foram criados nesta entrega.

## Antes do primeiro commit

- Confirmar proprietário, nome e visibilidade. Nome sugerido: `prisma` ou `prisma-demo`.
- Revisar direito de publicar o código e os ativos; escolher uma licença explicitamente.
- Usar uma pasta nova para o portfólio, sem copiar a árvore operacional inteira.
- Revisar conteúdo, caminhos, e-mails, endpoints, screenshots e histórico, se houver.
- Não adicionar bases, exports, logs, `.env`, mapeamentos privados, tokens ou ambientes virtuais.
- Verificar que todos os dados demonstrados são gerados do zero. Mascaramento/anonimização não é a estratégia desta demo.
- Executar os testes. A configuração de Actions só será validada após rodar no GitHub.

## Primeiro commit local (após revisão)

No terminal, na raiz desta pasta:

```bash
git init
git branch -M main
git add README.md .gitignore prisma tests docs requirements-api.txt .github identidade_prisma SHA256SUMS.txt
git diff --cached --stat
git diff --cached
git status
```

Leia o diff antes de confirmar. A seleção explícita reduz o risco de incluir arquivos extras; não substitui revisão. `.gitignore` não apaga segredos já versionados.

Depois de revisar:

```bash
git commit -m "feat: add synthetic Prisma demo database and local API"
```

Crie um repositório vazio em sua conta GitHub (sem README/licença/gitignore automáticos, para evitar históricos divergentes). Substitua os placeholders abaixo:

```bash
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

Use o fluxo de autenticação do Git/GitHub no seu computador. Não cole tokens na URL, no código ou no chat. Se o remoto já existir, inspecione `git remote -v` antes de alterá-lo; não sobrescreva remotos automaticamente.

Se decidir publicar depois de começar privado, revise todo o conteúdo e histórico antes de mudar a visibilidade. Credenciais expostas exigem revogação/rotação, não apenas exclusão do arquivo.

## Demonstração no README do GitHub

Descreva dados como sintéticos, as dez situações simuladas e a diferença entre candidatos e confirmação por referência. Não apresente as contagens da demo como resultados organizacionais. Não declare CI aprovada antes da execução nem FastAPI validado antes dos testes com dependências.

Quando o repositório existir, registrar sua URL na propriedade Link do projeto no Notion. Não definir a propriedade com uma URL presumida.

## Upload pelo navegador

Extrair o pacote em uma pasta limpa. Enviar o conteúdo de `prisma_central`, não a pasta externa nem o ZIP. `README.md` e `prisma/` devem ficar na raiz de `prisma-central`. Upload do GitHub não aplica `.gitignore`: não arrastar a pasta de execução com dados, ambientes virtuais ou arquivos internos.
