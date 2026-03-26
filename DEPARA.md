# 🔁 De/Para — Campos Blue Service BPM ↔ API Escavador v2

> Documento de referência para o time de Produto da Blue Service BPM.  
> Mapeia cada campo da plataforma jurídica ao respectivo caminho no JSON retornado pela API Escavador v2.

---

## 1. Capa do Processo

| Campo Blue Service BPM | Caminho no JSON Escavador v2 | Natureza | Observação |
|---|---|---|---|
| **Área** | `fonte.tipo` | Fixo | Ex: `"TRIBUNAL"`, `"STJ"` |
| **Assunto** (título do documento jurídico) | `assuntos[0].nome` | Fixo | Pode haver múltiplos assuntos no array |
| **Classe** (tipo do documento) | `classe` | Fixo | Ex: `"Ação Indenizatória"` |
| **Distribuição** | `data_distribuicao` | ⚡ Dinâmico | Formato ISO 8601 |
| **Situação** | `situacao` | ⚡ Dinâmico | Ex: `"Em andamento"`, `"Arquivado"` |
| **Valor da Causa** | `valor_causa` ou `informacoes_complementares["Valor da causa"]` | ⚡ Dinâmico | Numérico ou string formatada, varia por tribunal |
| **Juiz Relator** | `informacoes_complementares["Juiz"]` ou `informacoes_complementares["Relator"]` | ⚡ Dinâmico | Chave varia conforme o tribunal |
| **Órgão** | `orgao_julgador.nome` | ⚡ Dinâmico | Ex: `"3ª Vara Cível"` |
| **Sigla do Tribunal** | `sigla` | Fixo | Ex: `"TJSP"`, `"STJ"` |
| **Sistema** | `sistema` | Fixo | Ex: `"esaj"`, `"pje"` |
| **Número CNJ** | `numero_cnj` | Fixo | Chave primária do processo |
| **Segredo de Justiça** | `informacoes_complementares["Segredo de Justiça"]` | Fixo | Booleano; presente apenas quando aplicável |

---

## 2. Partes — Polo Ativo e Polo Passivo

Fonte: campo `envolvidos[]` no JSON da capa do processo.

| Campo Blue Service BPM | Caminho no JSON Escavador v2 | Natureza | Observação |
|---|---|---|---|
| **Polo** | `envolvidos[].polo` | Fixo | `"ATIVO"` ou `"PASSIVO"` |
| **Nome da Parte** | `envolvidos[].nome` | Fixo | Pessoa física ou jurídica |
| **Tipo da Parte** | `envolvidos[].tipo_normalizado` | Fixo | Ex: `"AUTOR"`, `"RÉU"`, `"ADVOGADO"` |
| **CPF** | `envolvidos[].cpf` | ⚡ Dinâmico | Disponível quando o tribunal expõe |
| **CNPJ** | `envolvidos[].cnpj` | ⚡ Dinâmico | Disponível quando o tribunal expõe |
| **Requerente / Requerido** | `envolvidos[].polo` = `"ATIVO"` / `"PASSIVO"` | Fixo | Equivale ao polo no Blue BPM |
| **Advogado (nome)** | `envolvidos[].advogados[].nome` | Fixo | Lista; uma parte pode ter múltiplos advogados |
| **OAB do Advogado** | `envolvidos[].advogados[].oab` | Fixo | Ex: `"OAB/SP 123456"` |

---

## 3. Movimentações (Andamentos)

Endpoint: `GET /api/v2/processos/numero_cnj/{cnj}/movimentacoes`

| Campo Blue Service BPM | Caminho no JSON Escavador v2 | Natureza | Observação |
|---|---|---|---|
| **Data do Andamento** | `itens[].data` | ⚡ Dinâmico | Formato ISO 8601 |
| **Tipo do Andamento** | `itens[].tipo` | ⚡ Dinâmico | Categoria da movimentação |
| **Tipo Inferido** | `itens[].tipo_inferido` | ⚡ Dinâmico | Classificação inteligente pelo Escavador |
| **Texto / Despacho** | `itens[].texto` | ⚡ Dinâmico | Conteúdo completo do andamento |
| **Citação** | `itens[].tipo_inferido` = `"CITACAO"` | ⚡ Dinâmico | Filtrar movimentações por tipo inferido |

---

## 4. Pedidos / Documentos

Endpoint: `GET /api/v2/processos/numero_cnj/{cnj}/documentos-publicos`

> ⚠️ **Atenção:** Este endpoint requer que se faça primeiro uma chamada `POST .../solicitar-atualizacao` para que o Escavador busque os documentos no tribunal. Os documentos ficam disponíveis de forma assíncrona.

| Campo Blue Service BPM | Caminho no JSON Escavador v2 | Natureza | Observação |
|---|---|---|---|
| **Pedido** (ex: dano moral, indenização) | `itens[].descricao` ou `itens[].nome` | ⚠️ Assíncrono | Conteúdo varia conforme o tribunal |
| **Tipo do Documento** | `itens[].tipo` | ⚠️ Assíncrono | Ex: `"PETIÇÃO"`, `"DECISÃO"`, `"DESPACHO"` |
| **Data do Documento** | `itens[].data` | ⚠️ Assíncrono | |
| **Key (download PDF)** | `itens[].key` | ⚠️ Assíncrono | Usar em `GET .../documentos/{key}` para baixar o PDF |
| **Autos (documentos restritos)** | endpoint `/autos` | ⚠️ Assíncrono | Requer certificado digital A1/A3 |

---

## 5. Exemplo de Estrutura JSON — Capa do Processo

```json
{
  "numero_cnj": "0000000-00.0000.0.00.0000",
  "classe": "Procedimento Comum Cível",
  "assuntos": [
    { "nome": "Indenização por Dano Moral" }
  ],
  "data_distribuicao": "2023-05-10T00:00:00",
  "situacao": "Em andamento",
  "valor_causa": 15000.00,
  "sigla": "TJSP",
  "sistema": "esaj",
  "orgao_julgador": {
    "nome": "3ª Vara Cível de São Paulo"
  },
  "fonte": {
    "tipo": "TRIBUNAL"
  },
  "informacoes_complementares": {
    "Juiz": "Dr. João da Silva",
    "Segredo de Justiça": false
  },
  "envolvidos": [
    {
      "nome": "Empresa ABC Ltda",
      "polo": "PASSIVO",
      "tipo_normalizado": "RÉU",
      "cnpj": "00.000.000/0001-00",
      "advogados": [
        { "nome": "Dr. Carlos Souza", "oab": "OAB/SP 99999" }
      ]
    },
    {
      "nome": "João da Silva",
      "polo": "ATIVO",
      "tipo_normalizado": "AUTOR",
      "cpf": "000.000.000-00",
      "advogados": [
        { "nome": "Dra. Maria Oliveira", "oab": "OAB/SP 88888" }
      ]
    }
  ]
}
```

---

## 6. Tabela Resumo para o Time de Produto

| Campo Blue BPM | JSON Escavador v2 | Natureza |
|---|---|---|
| Área | `fonte.tipo` | Fixo |
| Assunto | `assuntos[0].nome` | Fixo |
| Classe | `classe` | Fixo |
| Distribuição | `data_distribuicao` | ⚡ Dinâmico |
| Situação | `situacao` | ⚡ Dinâmico |
| Valor da Causa | `valor_causa` | ⚡ Dinâmico |
| Juiz Relator | `informacoes_complementares["Juiz"]` | ⚡ Dinâmico |
| Órgão | `orgao_julgador.nome` | ⚡ Dinâmico |
| Polo Ativo / Passivo | `envolvidos[].polo` | Fixo |
| Nome da Parte | `envolvidos[].nome` | Fixo |
| Tipo da Parte | `envolvidos[].tipo_normalizado` | Fixo |
| CPF / CNPJ | `envolvidos[].cpf` / `.cnpj` | ⚡ Dinâmico |
| Advogado | `envolvidos[].advogados[].nome` | Fixo |
| OAB | `envolvidos[].advogados[].oab` | Fixo |
| Andamento — Data | `movimentacoes.itens[].data` | ⚡ Dinâmico |
| Andamento — Texto/Despacho | `movimentacoes.itens[].texto` | ⚡ Dinâmico |
| Citação | `movimentacoes.itens[].tipo_inferido` = `"CITACAO"` | ⚡ Dinâmico |
| Pedidos | `documentos-publicos.itens[].descricao` | ⚠️ Assíncrono |
| Download PDF | `documentos-publicos.itens[].key` | ⚠️ Assíncrono |

> **Legenda:**
> - **Fixo** — retornado diretamente na consulta da capa (`GET /processos/numero_cnj/{cnj}`)
> - **⚡ Dinâmico** — pode variar conforme o tribunal ou atualização do processo
> - **⚠️ Assíncrono** — requer `POST .../solicitar-atualizacao` antes de consultar

---

## 7. Endpoints Utilizados

| Funcionalidade | Método | Endpoint Escavador v2 |
|---|---|---|
| Buscar capa + partes | `GET` | `/api/v2/processos/numero_cnj/{cnj}` |
| Listar movimentações | `GET` | `/api/v2/processos/numero_cnj/{cnj}/movimentacoes` |
| Solicitar atualização de docs | `POST` | `/api/v2/processos/numero_cnj/{cnj}/solicitar-atualizacao` |
| Status da atualização | `GET` | `/api/v2/processos/numero_cnj/{cnj}/status-atualizacao` |
| Listar documentos públicos | `GET` | `/api/v2/processos/numero_cnj/{cnj}/documentos-publicos` |
| Listar autos (restritos) | `GET` | `/api/v2/processos/numero_cnj/{cnj}/autos` |
| Download de PDF | `GET` | `/api/v2/processos/numero_cnj/{cnj}/documentos/{key}` |

---

## 8. API Escavador v1 vs v2 — Quando Usar Cada Uma

> O sistema utiliza **ambas** as versões da API Escavador. É importante entender a diferença entre elas.

| Aspecto | API v1 (`/api/v1/`) | API v2 (`/api/v2/`) |
|---|---|---|
| **Finalidade principal** | Monitoramento contínuo, buscas assíncronas por tribunal | Consulta direta de processos por CNJ |
| **Forma de busca** | Por CPF, CNPJ, nome ou OAB (busca ampla) | Por número CNJ (busca direta) |
| **Resultado** | Assíncrono — via polling ou webhook/callback | Síncrono (capa + partes) ou assíncrono (documentos) |
| **Monitoramentos** | ✅ Suportado (`/monitoramentos`) | ❌ Não disponível |
| **Callbacks / Webhooks** | ✅ Suportado (`/callbacks`) | ❌ Não disponível |
| **Documentos públicos** | ❌ Não disponível | ✅ Suportado (`/documentos-publicos`) |
| **Autos restritos** | ❌ Não disponível | ✅ Suportado (`/autos`) |
| **Base URL** | `https://api.escavador.com/api/v1` | `https://api.escavador.com/api/v2` |
| **Docs oficiais** | https://api.escavador.com/v1/docs/ | https://api.escavador.com/v2/docs/ |

---

## 9. API v1 — Monitoramento de Processos

> Base URL: `https://api.escavador.com/api/v1`  
> Autenticação: `Authorization: Bearer {ESCAVADOR_TOKEN}`  
> Docs oficiais: https://api.escavador.com/v1/docs/

O monitoramento permite que o sistema seja **notificado automaticamente** (via webhook/callback) quando há novas movimentações em processos vinculados a um CPF ou CNPJ monitorado, sem precisar fazer polling ativo.

### 9.1 Endpoints de Monitoramento

| Funcionalidade | Método | Endpoint v1 | Observação |
|---|---|---|---|
| Criar monitoramento | `POST` | `/api/v1/monitoramentos` | Monitora um CPF, CNPJ, nome ou OAB |
| Listar monitoramentos | `GET` | `/api/v1/monitoramentos` | Retorna todos os monitoramentos ativos |
| Detalhar monitoramento | `GET` | `/api/v1/monitoramentos/{id}` | Detalhes de um monitoramento específico |
| Atualizar monitoramento | `PUT` | `/api/v1/monitoramentos/{id}` | Atualiza configurações do monitoramento |
| Remover monitoramento | `DELETE` | `/api/v1/monitoramentos/{id}` | Encerra o monitoramento |

### 9.2 Campos do Payload — Criar Monitoramento (POST /api/v1/monitoramentos)

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `tipo` | string | ✅ | Tipo de monitoramento: `"cpf"`, `"cnpj"`, `"nome"`, `"oab"` |
| `valor` | string | ✅ | O valor a monitorar (ex: `"000.000.000-00"` para CPF) |
| `nome` | string | ❌ | Nome descritivo do monitoramento (para identificação) |
| `callback_url` | string | ❌ | URL de webhook para receber notificações de novas movimentações |

### 9.3 Campos da Resposta — Monitoramento

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | integer | ID único do monitoramento |
| `tipo` | string | Tipo monitorado: `"cpf"`, `"cnpj"`, `"nome"`, `"oab"` |
| `valor` | string | Valor sendo monitorado |
| `nome` | string | Nome descritivo |
| `ativo` | boolean | Se o monitoramento está ativo |
| `callback_url` | string | URL de webhook configurada |
| `criado_em` | string | Data de criação (ISO 8601) |

### 9.4 Exemplo — Criar Monitoramento

```json
// POST /api/v1/monitoramentos
// Request:
{
  "tipo": "cnpj",
  "valor": "00.000.000/0001-00",
  "nome": "Empresa ABC Ltda",
  "callback_url": "https://meu-sistema.com/webhook/escavador"
}

// Response:
{
  "id": 12345,
  "tipo": "cnpj",
  "valor": "00.000.000/0001-00",
  "nome": "Empresa ABC Ltda",
  "ativo": true,
  "callback_url": "https://meu-sistema.com/webhook/escavador",
  "criado_em": "2026-01-01T10:00:00"
}
```

---

## 10. API v1 — Buscas Assíncronas por Tribunal

> Permitem iniciar buscas de processos em tribunais específicos por CPF/CNPJ, nome ou OAB, recebendo os resultados de forma assíncrona.

### 10.1 Endpoints de Busca Assíncrona

| Funcionalidade | Método | Endpoint v1 | Observação |
|---|---|---|---|
| Listar origens (tribunais) | `GET` | `/api/v1/tribunal/origens` | Retorna todos os códigos de tribunais disponíveis |
| Busca por CPF/CNPJ (async) | `POST` | `/api/v1/tribunal/{origem}/busca-por-documento/async` | `{origem}` = código do tribunal (ex: `tjsp`) |
| Busca por nome (async) | `POST` | `/api/v1/tribunal/{origem}/busca-por-nome/async` | Busca por nome da parte |
| Busca por OAB (async) | `POST` | `/api/v1/tribunal/{origem}/busca-por-oab/async` | Busca por número OAB do advogado |
| Buscar resultados (todos) | `GET` | `/api/v1/async/resultados` | Lista resultados de buscas assíncronas pendentes/concluídas |
| Buscar resultado por ID | `GET` | `/api/v1/async/resultados/{id}` | Resultado de uma busca assíncrona específica |

### 10.2 Fluxo Típico de Busca Assíncrona

```
1. GET /api/v1/tribunal/origens          → descobre os códigos dos tribunais
2. POST /api/v1/tribunal/tjsp/busca-por-documento/async  → inicia busca no TJSP
3. Polling: GET /api/v1/async/resultados  → aguarda resultado ficar disponível
   OU recebe via callback/webhook configurado
4. GET /api/v1/async/resultados/{id}      → lê os processos encontrados
```

### 10.3 Campos do Payload — Busca por Documento

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `documento` | string | ✅ | CPF ou CNPJ (com ou sem formatação) |
| `tipo_documento` | string | ✅ | `"cpf"` ou `"cnpj"` |

### 10.4 Campos da Resposta — Resultado Assíncrono

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | integer | ID da busca assíncrona |
| `status` | string | `"pendente"`, `"concluido"`, `"erro"` |
| `processos` | array | Lista de processos encontrados (quando `status = "concluido"`) |
| `processos[].numero_cnj` | string | Número CNJ do processo |
| `processos[].tribunal` | string | Sigla do tribunal |
| `processos[].classe` | string | Classe do processo |
| `processos[].data_distribuicao` | string | Data de distribuição (ISO 8601) |

---

## 11. API v1 — Callbacks e Webhooks

> Os callbacks são notificações enviadas pela API Escavador ao sistema quando há atualizações nos processos monitorados ou quando buscas assíncronas são concluídas.

### 11.1 Endpoints de Callback

| Funcionalidade | Método | Endpoint v1 | Observação |
|---|---|---|---|
| Listar callbacks recebidos | `GET` | `/api/v1/callbacks` | Lista callbacks enviados pelo Escavador ao sistema |
| Marcar callbacks como recebidos | `POST` | `/api/v1/callbacks/marcar-recebidos` | Confirma recebimento dos callbacks (evita reenvio) |

### 11.2 Parâmetros — Listar Callbacks (GET /api/v1/callbacks)

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `data_inicio` | string | Filtrar callbacks a partir desta data (ISO 8601) |
| `data_fim` | string | Filtrar callbacks até esta data (ISO 8601) |
| `tipo` | string | Filtrar por tipo de evento |

### 11.3 Estrutura do Payload de Callback (recebido no webhook)

| Campo | Tipo | Descrição |
|---|---|---|
| `tipo_evento` | string | Tipo do evento: `"nova_movimentacao"`, `"busca_concluida"`, etc. |
| `monitoramento_id` | integer | ID do monitoramento que gerou o evento |
| `processo` | object | Dados do processo atualizado |
| `processo.numero_cnj` | string | Número CNJ do processo |
| `movimentacoes` | array | Novas movimentações detectadas (quando aplicável) |
| `movimentacoes[].data` | string | Data da movimentação (ISO 8601) |
| `movimentacoes[].texto` | string | Texto/despacho da movimentação |
| `movimentacoes[].tipo_inferido` | string | Classificação inteligente da movimentação |

### 11.4 Configuração do Webhook no Sistema

O sistema Blue Service recebe callbacks no endpoint interno configurado via variável de ambiente:

```
WEBHOOK_AUTH_TOKEN=<token-de-autenticação-do-webhook>
```

O token é validado em cada requisição recebida para garantir que o callback é legítimo.

---

## 12. Tabela Geral — Todos os Endpoints Utilizados (v1 + v2)

### API v2 — Consulta Direta por CNJ

| Funcionalidade | Método | Endpoint |
|---|---|---|
| Buscar capa + partes | `GET` | `/api/v2/processos/numero_cnj/{cnj}` |
| Listar movimentações | `GET` | `/api/v2/processos/numero_cnj/{cnj}/movimentacoes` |
| Solicitar atualização de docs | `POST` | `/api/v2/processos/numero_cnj/{cnj}/solicitar-atualizacao` |
| Status da atualização | `GET` | `/api/v2/processos/numero_cnj/{cnj}/status-atualizacao` |
| Listar documentos públicos | `GET` | `/api/v2/processos/numero_cnj/{cnj}/documentos-publicos` |
| Listar autos (restritos) | `GET` | `/api/v2/processos/numero_cnj/{cnj}/autos` |
| Download de PDF | `GET` | `/api/v2/processos/numero_cnj/{cnj}/documentos/{key}` |

### API v1 — Monitoramento e Buscas Assíncronas

| Funcionalidade | Método | Endpoint |
|---|---|---|
| Criar monitoramento | `POST` | `/api/v1/monitoramentos` |
| Listar monitoramentos | `GET` | `/api/v1/monitoramentos` |
| Detalhar monitoramento | `GET` | `/api/v1/monitoramentos/{id}` |
| Atualizar monitoramento | `PUT` | `/api/v1/monitoramentos/{id}` |
| Remover monitoramento | `DELETE` | `/api/v1/monitoramentos/{id}` |
| Listar origens (tribunais) | `GET` | `/api/v1/tribunal/origens` |
| Busca por documento (async) | `POST` | `/api/v1/tribunal/{origem}/busca-por-documento/async` |
| Busca por nome (async) | `POST` | `/api/v1/tribunal/{origem}/busca-por-nome/async` |
| Busca por OAB (async) | `POST` | `/api/v1/tribunal/{origem}/busca-por-oab/async` |
| Listar resultados async | `GET` | `/api/v1/async/resultados` |
| Resultado async por ID | `GET` | `/api/v1/async/resultados/{id}` |
| Listar callbacks | `GET` | `/api/v1/callbacks` |
| Marcar callbacks recebidos | `POST` | `/api/v1/callbacks/marcar-recebidos` |
