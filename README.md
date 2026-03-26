# 🔍 Monitor Jurídico — Blue Service BPM

Sistema de monitoramento de processos judiciais integrado com a **API Escavador** (v1 e v2).

## Visão Geral

O Monitor Jurídico permite:
- Cadastrar CPFs e CNPJs para monitoramento contínuo de processos
- Consultar capas, partes e movimentações de processos por número CNJ
- Receber notificações automáticas (webhooks) de novas movimentações
- Acessar e baixar documentos públicos e autos de processos
- Visualizar histórico de andamentos e citações

## Arquivos Principais

| Arquivo | Descrição |
|---|---|
| `app_monitor_juridico.py` | Aplicação principal (Flask) — versão atual (v6+) |
| `_app_monitor_juridico.py` | Versão anterior (backup/referência) |
| `DEPARA.md` | De/Para completo: campos Blue Service BPM ↔ Escavador v1 e v2 |
| `.env` | Variáveis de ambiente (NÃO commitar — ver `.gitignore`) |
| `escavador_monitor.db` | Banco SQLite local de cache |

## APIs Utilizadas

| Versão | Base URL | Finalidade |
|---|---|---|
| **v1** | `https://api.escavador.com/api/v1` | Monitoramentos, buscas assíncronas, callbacks |
| **v2** | `https://api.escavador.com/api/v2` | Consulta direta por CNJ, documentos, movimentações |

## Endpoints Internos (Flask)

### Interface de Usuário
| Rota | Descrição |
|---|---|
| `GET /ui/documentacao` | Exibe o DEPARA.md renderizado como HTML |
| `GET /ui/docs-v2/<CNJ>` | Mini-formulário para consultar documentos de um processo |
| `GET /ui/<CNJ>` | Painel completo do processo (capa, partes, movimentações, docs) |

### API de Processos (v2)
| Rota | Método | Descrição |
|---|---|---|
| `/processos/<CNJ>` | `GET` | Capa + partes do processo |
| `/processos/<CNJ>/movimentacoes` | `GET` | Movimentações do processo |
| `/processos/<CNJ>/documentos-publicos` | `GET` | Lista documentos públicos (cache + API) |
| `/processos/<CNJ>/autos` | `GET` | Lista autos restritos (cache + API) |
| `/processos/<CNJ>/solicitar-atualizacao` | `POST` | Solicita atualização de documentos no tribunal |
| `/processos/<CNJ>/solicitar-status` | `GET` | Status da última solicitação de atualização |
| `/processos/<CNJ>/documentos/<key>` | `GET` | Download de PDF de documento |

### Watchlist (Monitoramentos — API v1)
| Rota | Método | Descrição |
|---|---|---|
| `/watchlist` | `GET` | Lista CPFs/CNPJs monitorados |
| `/watchlist` | `POST` | Adiciona CPF/CNPJ ao monitoramento |
| `/watchlist/<doc>` | `DELETE` | Remove CPF/CNPJ do monitoramento |

### Webhook / Callbacks
| Rota | Método | Descrição |
|---|---|---|
| `/webhook/escavador` | `POST` | Recebe callbacks do Escavador (novas movimentações) |

## Variáveis de Ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `ESCAVADOR_TOKEN` | ✅ | Token JWT de acesso à API Escavador |
| `WEBHOOK_AUTH_TOKEN` | ❌ | Token de autenticação para validar callbacks recebidos |
| `ESCAVADOR_BASE` | ❌ | Base URL da API v2 (padrão: `https://api.escavador.com/api/v2`) |
| `DB_PATH` | ❌ | Caminho do banco SQLite (padrão: `./escavador_monitor.db`) |
| `POLL_INTERVAL_SECONDS` | ❌ | Intervalo de polling em segundos (padrão: `300`) |
| `AUTO_DISCOVER_ENABLED` | ❌ | Habilita descoberta automática de processos (`0` ou `1`) |
| `HOST` | ❌ | Host do servidor Flask (padrão: `0.0.0.0`) |
| `PORT` | ❌ | Porta do servidor Flask (padrão: `5000`) |

## Banco de Dados (SQLite)

O sistema mantém um banco SQLite local (`escavador_monitor.db`) com as seguintes tabelas principais:

| Tabela | Descrição |
|---|---|
| `watchlist` | CPFs/CNPJs cadastrados para monitoramento |
| `processos` | Cache de capas de processos consultados |
| `movimentacoes` | Histórico de movimentações |
| `docs_v2_cache` | Cache de documentos públicos e autos (v2) |
| `updates_v2` | Registro de solicitações de atualização de documentos |

## ⚠️ Segurança

- **Nunca commitar o arquivo `.env`** — ele contém o token JWT da API Escavador
- Adicionar `Monitor Juridico/.env` ao `.gitignore` se ainda não estiver
- Rotacionar o `ESCAVADOR_TOKEN` regularmente no painel em https://api.escavador.com

## Documentação de Referência

- [DEPARA.md](DEPARA.md) — Mapeamento completo de campos Blue Service BPM ↔ Escavador (v1 e v2)
- [API Escavador v1](https://api.escavador.com/v1/docs/) — Monitoramentos, buscas assíncronas
- [API Escavador v2](https://api.escavador.com/v2/docs/) — Consulta por CNJ, documentos
