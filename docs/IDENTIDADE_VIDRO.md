# Identidade 1.3.1 — Aurora, Nocturne e transparência

## Conceito

Um prisma triangular de vidro recebe as perspectivas Omnichannel, CRM e ERP Core e as traduz em uma leitura rastreável. É uma metáfora visual: não simula óptica física, mede conversão comercial ou promete fusão de cadastros.

## Hierarquia visual

- Superfícies de vidro com a paleta original Aurora (claro azulado) e Nocturne (azul-marinho). Acentos azuis restaurados; roxo continua detalhe de marca.
- Vidro fosco: translucidez, backdrop blur, reflexão suave e borda iluminada.
- Roxo apenas como assinatura da marca, detalhe de navegação ativa e identificação Prisma. Não tingir toda a tela.
- Vermelho Omnichannel, azul CRM e verde ERP Core identificam origem, não confiança ou qualidade. Estados continuam acompanhados de rótulos textuais.
- Texto e números de indicadores em cores neutras; vidro não deve reduzir legibilidade.

## Ativos

`identidade_prisma/Prisma_Identidade_Visual.html`: guia autônomo offline com Claro/Escuro/Sistema, quatro perspectivas e regras.

`prisma-symbol*.svg` e `prisma-wordmark*.svg`: símbolo triangular e assinatura para fundo claro/escuro.

`prisma-tokens.json`: tokens da revisão; `prisma.css`: estilos do guia. O painel usa `prisma/web/panel.css`.

## Comportamento e limites

Preferência de movimento reduzido elimina transições/animações. Há superfícies opacas alternativas quando backdrop-filter não é suportado ou quando transparência reduzida é solicitada. Tabelas largas rolam dentro de sua região, nunca a página inteira.

O painel permanece somente leitura, independente da organização e inteiramente sintético. Coincidência de contato continua candidato; múltiplos destinos ou evidências divergentes exigem revisão. Transformar a leitura de múltiplos canais não significa unir pessoas.

## Aplicar a atualização

Pare o painel, faça backup e copie o conteúdo de `prisma_central` para a pasta demo, preservando `data/`, `snapshots/` e `.venv`. Reinicie com o mesmo comando do README e use Ctrl+F5 no navegador. Não atualizar a instalação operacional com este pacote.
