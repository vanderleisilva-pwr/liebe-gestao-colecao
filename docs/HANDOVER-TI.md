# Handover Técnico — Liebe · Gestão de Coleção

Documento para o **time de TI da Liebe** assumir a manutenção da aplicação. Resume arquitetura, como rodar, como publicar e o caminho de evolução. Contexto de negócio e manual do usuário final estão no [README.md](../README.md) e na própria aplicação (página "Manual de Uso").

> **Status:** protótipo de validação em produção (uso interno). Operadora principal: Joice (Coordenadora de Produto). Próxima fase planejada: migração para Next.js + Supabase (multiusuário em tempo real).

---

## 1. O que é, em uma frase

Sistema de gestão do cronograma de coleção (substitui uma planilha Excel + caderno), construído como **site estático de arquivo único** — sem build, sem backend, sem dependências de runtime. Roda 100% no navegador, persistindo em `localStorage`.

## 2. Stack e decisões de arquitetura

- **HTML + CSS + JavaScript vanilla**, sem framework e **sem etapa de build**. O deploy é o próprio repositório servido como arquivos estáticos.
- **Sem backend / sem banco** nesta fase: o estado vive em `localStorage` do navegador. Implicação operacional: **os dados são por-máquina** — a máquina da Joice é a fonte da verdade até a migração. O app tem export/import JSON e export Excel para backup.
- **Por que vanilla single-file:** validação rápida com o cliente sem custo de infraestrutura. O modelo de dados já nasceu espelhando tabelas relacionais (ver §6) para que a migração seja direta.

## 3. Estrutura do repositório

```
liebe-gestao-colecao/
├── index.html          # APLICAÇÃO INTEIRA: CSS + router (hash) + store + 6 páginas + tour + export/import
├── data.js             # window.LIEBE_SEED — dados-semente extraídos da planilha (NÃO editar à mão)
├── scripts/
│   └── gerar_seed.py   # regenera data.js a partir do .xlsx (requer Python 3 + openpyxl)
├── vercel.json         # config de deploy estático (sem build, headers noindex/segurança)
├── README.md           # visão geral, manual resumido, mapa de migração Supabase
└── docs/HANDOVER-TI.md # este arquivo
```

### Anatomia do `index.html` (ordem do `<script>`)
`helpers → STORE (localStorage + migrate versionado) → SELECTORS (status/KPIs derivados) → ROUTER/SHELL → VIEWS (uma função por página) → MODAIS → AÇÕES (event delegation) → TOUR → init`.

Convenções para manutenção:
- **Nenhuma função de render acopla listeners por elemento** — tudo é *event delegation* via `data-action` no `document`. Para adicionar um botão, dê a ele `data-action="x"` e registre `ACTIONS['x']`.
- **Status nunca é armazenado** — é sempre derivado (`statusProcesso`, `statusCelula`) comparando datas com "hoje". Datas em `'YYYY-MM-DD'`; diferença via `Date.UTC` (imune a fuso).
- **Toda mutação passa por `commit(fn)`** → aplica, salva (debounce) e re-renderiza. Não escrever no DOM e no estado em separado.
- **Migrações de schema:** array `MIGRATIONS` + `schema_version` (mesmo padrão a usar no Postgres).
- **Versão da planilha:** `seed_version` (timestamp do .xlsx). Quando o `data.js` traz versão mais nova que a salva, o app oferece atualizar o catálogo preservando dados operacionais.

## 4. Rodar localmente

Não precisa de Node. Qualquer servidor estático serve (precisa ser via HTTP, não `file://`, por causa do `data.js`):

```bash
# Python (já usado no projeto)
python -m http.server 4173
# abra http://localhost:4173

# ou, se preferir Node:
npx serve .
```

Login do protótipo: escolher o usuário e digitar o PIN (padrão **1234**, definido em `data.js`). É identificação para autoria, **não** segurança.

## 5. Atualizar os dados da coleção (regenerar o seed)

Quando vier uma nova planilha/coleção:

```bash
pip install openpyxl            # uma vez
python scripts/gerar_seed.py "C:\caminho\para\GESTÃO DA COLEÇÃO ... .xlsx"
```

O script lê as abas `CRONOGRAMA.V2`, `GESTÃO DA COLEÇÃO` e `Auditoria` e reescreve `data.js`. Commit + push → a Vercel publica sozinha. Usuários com dados salvos verão a faixa "atualizar coleção".

## 6. Deploy (Vercel)

Site estático, **sem build command**. Conectado ao GitHub: cada `push` na branch `main` gera um deploy automático (Production). Pré-visualizações por PR vêm de graça.

Configuração na Vercel (Project Settings):
- Framework Preset: **Other**
- Build Command: *(vazio)* · Output Directory: **`.`** · Install Command: *(vazio)*
- O `vercel.json` já fixa isso e adiciona headers `noindex` (é app interno) e de segurança básica.

## 7. Modelo de dados → tabelas Supabase (fase 2)

Cada coleção do `LIEBE_SEED` vira uma tabela 1:1 (snake_case, UUIDs, FKs, datas ISO):

| Estrutura no app | Tabela | Observação |
|---|---|---|
| `users` | `users` | trocar `pin` por Supabase Auth (Google domínio `@liebe...`) |
| `collections` | `collections` | |
| `collections` | `collections` | uma linha por coleção; `marcos {entrega_mostruario, liberacao_pcp_seq}` define o alvo do caminho crítico daquela coleção. Todo o cronograma é filtrado por `collection_id` |
| `phases` | `phases` | catálogo das 19 fases |
| `phase_deadlines` | `phase_deadlines` | data-limite por fase × coleção |
| `macro_processes` | `macro_processes` | 40 processos; `start_date`/`end_date` = linha de base congelada · `inicio_real`/`fim_real` = realizado (digitado na plataforma) · `predecessores` (array de `seq`) · `macro_tema` · `responsavel_user_id` (dono, FK users) · `motivo_atraso` (enum `MOTIVOS_ATRASO`) · `promessas[]` (append-only: `{data, feita_em, feita_por}` → vira tabela própria no Postgres). Status, projeção, margem, caminho crítico e desfecho das promessas são **derivados**, nunca persistidos |
| `references` | `references` | ~112 referências, filtradas por `collection_id`; as criadas na plataforma têm id `ref-m-…` e sobrevivem à troca de planilha (com suas `reference_phases`). `collection_name` guarda o rótulo do time (coluna "COLEÇÃO" da grade), que não define a coleção; campo `status` ('ativa'/'cancelada') + snapshot do cancelamento. Cancelar/reativar é exclusivo da Joice (`canCancelRefs()`) |
| `reference_phases` | `reference_phases` | célula do grid (esparsa) |
| `reference_log` | `reference_log` | trilha append-only de cancelamentos/reativações de referência (governança) |
| `tasks` | `tasks` | |
| `rituals` (campo `attendance` aninhado) | `rituals` + `ritual_attendance` | normalizar a presença |
| `charges` | `charges` | cobranças documentadas |
| `kpi_entries` | `kpi_entries` | KPIs manuais (RNC, Atraso de MP) |
| `bypass_log` | `bypass_log` | estrutura pronta; UI prevista p/ v2 |

Migração = um `INSERT` por entidade lendo o export JSON do app. KPIs e status continuam derivados (nada a migrar além dos fatos).

## 8. Backlog conhecido / v2

- Pré-custos por referência (aba existe na planilha, hoje quase vazia).
- Reporte mensal à Diretoria gerado automaticamente dos dados.
- Medidor de Taxa de Bypass (≤ 2/mês) — `bypass_log` já modelado.
- Multiusuário em tempo real (Supabase) — resolve o limite "dados por-máquina".

---
*PWR Gestão · Vanderlei Silva · contato do projeto. Confidencial — uso interno Liebe.*
