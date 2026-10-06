# Contrato público — Prisma Demo 0.1

Contrato criado para o portfólio. Não é cópia nem comprovação de compatibilidade com APIs privadas.

## Rotas

| GET | Paginação/filtros |
| --- | --- |
| `/health` | Sem parâmetros |
| `/api/demo/meta` | Manifesto de geração; sem parâmetros |
| `/api/demo/core/companies` | Lista das duas empresas fictícias |
| `/api/demo/core/customers` | `page` (padrão 1), `page_size` (padrão 25; 1–100), `company_id`, `updated_since` |
| `/api/demo/crm/contacts` | `limit` (padrão 25; 1–100), `cursor`, `updated_since` |
| `/api/demo/omnichannel/customers` | `limit`, `cursor`, `updated_since` |
| `/api/demo/omnichannel/conversations` | `limit`, `cursor`, `updated_since` |
| `/api/demo/omnichannel/conversations/{conversation_id}/messages` | `limit`, `cursor`; ID `DEMO-CONV-00001` como exemplo |

Ordenação: `(updated_at, id)` nas listas paginadas; `(created_at, id)` nas mensagens. `updated_since` é exclusivo (`>`), requer timestamp com timezone e sem frações; é normalizado para UTC. Não é data de criação. Para extratores incrementais de produção, usar checkpoint composto ou sobreposição e deduplicação: filtrar apenas por timestamp pode perder registros com o mesmo horário. Esta versão extrai snapshots completos; checkpoint persistido ainda não foi implementado.

## Envelopes distintos

Core:

```json
{
  "data": [],
  "pagination": {"page": 1, "page_size": 25, "total": 0, "next_page": null},
  "meta": {"synthetic": true, "source": "core", "available": true, "snapshot_at": "2026-01-15T12:00:00Z", "dataset": "HASH"}
}
```

CRM:

```json
{
  "results": [],
  "paging": {"next": null},
  "meta": {"synthetic": true, "source": "crm", "available": true, "snapshot_at": "2026-01-15T12:00:00Z", "dataset": "HASH"}
}
```

Quando há próxima página, `paging.next.after` contém o cursor; enviá-lo como query `cursor` mantendo `limit` e filtros.

Omnichannel:

```json
{
  "items": [],
  "nextCursor": null,
  "meta": {"synthetic": true, "source": "omnichannel", "available": true, "snapshot_at": "2026-01-15T11:00:00Z", "dataset": "HASH"}
}
```

Esses exemplos explicam a forma, não as contagens padrão. Os horários distintos demonstram por que cobertura de snapshot não prova presença/ausência em tempo real.

## Campos por fonte

- Core: `id`, `company_id`, `customer_id`, `name`, `email`, `phone`, `document`, `city`, `updated_at`.
- CRM: `id`, `properties` (`firstname`, `lastname`, `email`, `phone`, `core_reference`, `lifecycle_stage`), `updatedAt`.
- Omnichannel: `id`, `name`, `contacts` (`email`, `phone`), `customFields.core_reference`, `channel`, `updatedAt`.
- Conversas: `id`, `customer_id`, `status`, `channel`, `created_at`, `updated_at`.
- Mensagens: `id`, `conversation_id`, `sender`, `text`, `created_at`.

Campos de domínio e IDs são convenções públicas próprias. O ID nativo CRM nunca é automaticamente uma referência Core.

## Cursor

Token opaco vinculado à rota, filtros, tamanho da página e fingerprint da base. Não reutilizar em outra consulta nem após regeneração. Não é token de autenticação e não carrega a verdade de referência. A API é local, sem autorização por usuário e não projetada para adversários ou produção.

## Erros

| HTTP | Significado |
| --- | --- |
| 400 | Parâmetro repetido/desconhecido, valor inválido ou cursor incompatível |
| 404 | Rota ou conversa inexistente |
| 405 | Método de escrita não permitido |
| 409 | Base regenerada; reiniciar API |
| 503 | Fonte sintética indisponível; não interpretar como zero |

O servidor padrão também retorna 414 para URLs excessivamente longas. O adaptador FastAPI usa o roteamento padrão de erros 404/405 e não necessariamente o mesmo envelope nessas duas respostas. As rotas funcionais e erros do serviço compartilham o mesmo núcleo.

O modo padrão oferece apenas JSON. `/docs` e `/openapi.json` existem somente no adaptador FastAPI. Não há autenticação, CORS permissivo, escrita, envio de mensagens ou chamadas externas.
