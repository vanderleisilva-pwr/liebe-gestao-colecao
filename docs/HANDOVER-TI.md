# Handover Técnico — Liebe · Gestão de Coleção

Documento para o **time de TI da Liebe** assumir a aplicação e construir o backend. Contexto de negócio e manual do usuário final estão no [README.md](../README.md) e na própria aplicação (página "Manual de Uso"). Convenções de código para quem for mexer no front atual estão em [CLAUDE.md](../CLAUDE.md).

> **Status:** protótipo validado e em uso real pelo setor de Estilo & Produto. Roda como site estático, sem backend, com os dados no `localStorage` do navegador. **Operadora principal: Joice (Coordenadora de Produto) — a máquina dela é hoje a fonte da verdade.**
>
> **O que se pede ao TI:** construir o backend que remove essa limitação, **sem reimplementar errado as regras de cronograma** descritas na §5. Elas são o produto.

---

## 1. O que você está recebendo

```
liebe-gestao-colecao/
├── index.html          # APLICAÇÃO INTEIRA: CSS + router (hash) + store + 8 páginas + tour + export
├── data.js             # window.LIEBE_SEED — dados extraídos das planilhas (NÃO editar à mão)
├── scripts/
│   └── gerar_seed.py   # regenera data.js a partir dos .xlsx (Python 3 + openpyxl)
├── vercel.json         # deploy estático, sem build
├── README.md           # visão geral e manual resumido
├── CLAUDE.md           # convenções de código — leitura obrigatória antes de editar
└── docs/
    ├── HANDOVER-TI.md  # este arquivo
    └── PROJETO.md      # histórico de decisões e o porquê de cada uma
```

HTML + CSS + JavaScript **vanilla**, sem framework e **sem etapa de build**. Dependências externas: apenas Google Fonts e SheetJS (carregado sob demanda no export). Rodar local:

```bash
python -m http.server 4173     # precisa ser via HTTP, não file://
```

Login atual: escolher o usuário e digitar o PIN (padrão `1234`). **Isso é identificação para autoria, não autenticação** — ver §7.

## 2. O que o backend precisa resolver

Em ordem de dor:

1. **Dados por-máquina.** Tudo vive no `localStorage` de um navegador. Se a Joice trocar de máquina, limpar o cache ou sair de férias, o histórico da coleção vai junto. Há export/import JSON como paliativo, e o app cobra backup a cada 7 dias.
2. **Sem multiusuário.** Anna, Camila e Joice não veem o mesmo estado. Hoje isso é contornado com uma pessoa digitando por todas.
3. **Sem autenticação real.** O PIN é um rótulo de autoria; qualquer um escolhe qualquer perfil.
4. **Limite de armazenamento.** ~5 MB por navegador. Com as fotos das peças isso passou a importar — o app já reduz cada foto para ~15 KB e mostra um medidor de uso.
5. **Sem auditoria consolidada.** Existe trilha de cancelamento de referência (`reference_log`) e histórico de promessas, mas não um log geral de quem mudou o quê.

O que **não** se pede mudar: a linguagem da interface (pt-BR, vocabulário de chão de fábrica, sem jargão de gestão de projetos em inglês) e a identidade visual da Liebe. São decisões do cliente, registradas no `CLAUDE.md`.

## 3. Trabalhar nesta base (manutenção e evolução)

A aplicação inteira é um arquivo: `index.html` — CSS no `<head>`, um `<script>` no fim. Não há framework, bundler nem etapa de build. Isso é decisão consciente (validação rápida sem infraestrutura) e deve ser mantida **até** a migração para o backend; a partir daí, a escolha de stack é de vocês.

### Anatomia do `<script>` — a ordem importa

```
helpers → STORE (localStorage + migrate versionado) → SELECTORS (motor + derivados)
→ ROUTER/SHELL → VIEWS (uma função por página) → MODAIS → AÇÕES → TOUR → init
```

Não reordene os blocos. As views chamam os selectors, que chamam os helpers; as ações mutam via `commit()` e disparam re-render.

### Convenções obrigatórias

| Regra | Por quê |
|---|---|
| Toda mutação passa por **`commit(fn)`** | aplica, salva com debounce, re-renderiza e respeita permissão. Nunca mexer no DOM e no estado em separado |
| **Event delegation**, nunca listener por elemento | botão novo recebe `data-action="x"` e você registra `ACTIONS['x']=(data,el,e)=>{}`. Os handlers globais já estão no `document` |
| **`esc()`** em toda interpolação de dado | proteção XSS — os dados vêm de planilha e de digitação livre |
| Datas sempre **`'YYYY-MM-DD'`**, diferença via **`diffDias()`** | usa `Date.UTC`, imune a fuso. `addDias()` para somar |
| Status e KPIs **sempre derivados** | ver §7 |
| Leitura escopada pelos seletores de coleção | `procsCol()`, `refsCol()`, `deadlinesCol()`, `tasksCol()`, `ritualsCol()`. **Nunca** ler `db.macro_processes` / `db.references` direto numa view — faz uma coleção contaminar a outra |
| UI em **pt-BR**, vocabulário de chão de fábrica | decisão do cliente: "margem de manobra", não "folga/float"; "o que empurra", não "caminho crítico" |
| Paleta só com as variáveis do `:root` | identidade da Liebe (rosé). Proibido usar as cores da PWR dentro do produto do cliente |

### Como fazer as alterações mais comuns

- **Campo novo numa entidade** → acrescente uma função ao array `MIGRATIONS` (idempotente), ajuste o modal e, se o dado for digitado na plataforma, **inclua-o na preservação** do `applyNewSeed()` (ver §6). Esquecer esse último passo apaga o dado do time na próxima planilha.
- **Tela nova** → função `vNome()` + entrada em `ROUTES`. O menu lateral se monta sozinho a partir de `ROUTES`.
- **Botão novo** → `data-action` no markup + `ACTIONS['...']`. Se for de escrita, dê a classe `.w` (o CSS esconde para o perfil `leitura`).
- **Coluna nova vinda da planilha** → ajuste `scripts/gerar_seed.py`. Cabeçalhos e colunas são localizados **pelo nome** (`achar_linha`, `mapa_colunas`), nunca por posição fixa — a planilha do cliente já ganhou colunas no meio duas vezes e quebrou o gerador em silêncio.

### Migrações de schema

`MIGRATIONS` é um array de funções `db => void` aplicadas em sequência; `migrate()` incrementa `schema_version` sozinho. Estado atual: **schema 7, 6 migrações**. Regras: **idempotente**, nunca reordenar, nunca editar uma migração já publicada (crie a próxima).

> Ler o array inteiro antes de modelar o banco vale o tempo: cada migração documenta um problema real. A v6→v7, por exemplo, religa referências que ficaram órfãs quando a modelagem de coleção mudou — e que sumiram de todas as telas em produção.

### Testar

Não há framework de teste no repo. O que existe e funciona bem:

```bash
# 1. extrai o <script> do index.html e confere a sintaxe
python scripts/extrai_script.py
node --check .tmp/app.js

# 2. suíte do motor de cronograma — roda sobre o data.js real, sem navegador
node scripts/teste_motor.js
```

A suíte cobre as regras da §6 com os dados reais (17 verificações). **Rode-a a cada mudança no motor** — os bugs mais caros deste projeto foram todos de cálculo silencioso, não de tela. Vale portá-la para o backend.

Para conferir no navegador, o app expõe tudo no escopo global: abra o console e chame `projetarCronograma(hojeStr())`, `panoramaCronograma(hojeStr())`, `simularAtraso(16,10,hojeStr())`.

### Fluxo de trabalho

```bash
python -m http.server 4173          # rodar local (precisa ser HTTP, não file://)
git push origin main                # a Vercel publica sozinha (estático, sem build)
```

Deploy: Vercel conectada ao GitHub, `main` → produção. Framework Preset **Other**, sem build command, output `.` — já fixado no `vercel.json`, que também põe headers `noindex` (app interno).

Regenerar o seed quando vier planilha nova:

```bash
pip install openpyxl
python scripts/gerar_seed.py "GESTÃO DA COLEÇÃO ... .xlsx" --colecao "CRONOGRAMA VERÃO 28.xlsx"
```

O `seed_version` é o **maior mtime entre todas as planilhas** — é o que dispara a faixa "atualizar coleção" para quem já tem dados salvos. Se olhar só a principal, acrescentar uma coleção não avisa ninguém (aconteceu).

### Onde está o "porquê"

- **`CLAUDE.md`** — convenções e as regras de negócio que não podem ser quebradas, em formato operacional. Escrito para agentes de IA, mas é a referência mais densa para qualquer dev.
- **`docs/PROJETO.md`** — histórico das decisões e o contexto de cada uma.
- **Mensagens de commit** — cada uma explica o problema que resolveu, não só o que mudou.

## 4. Modelo de dados

O modelo já nasceu espelhando tabelas relacionais (snake_case, FKs, datas ISO `YYYY-MM-DD`). O estado atual está em `schema_version = 7`, com 6 migrações aplicadas em sequência (o array `MIGRATIONS` no `index.html` é o histórico — vale ler antes de modelar, porque cada migração existe por um motivo).

### DDL sugerido (Postgres / Supabase)

```sql
create table collections (
  id            text primary key,
  name          text not null,
  status        text not null default 'em_andamento',
  start_date    date,
  end_date      date,
  -- marcos do caminho crítico DESTA coleção
  entrega_mostruario  date,
  liberacao_pcp_seq   int,      -- seq da etapa "Liberação da coleção para PCP"
  copiada_de    text references collections(id),
  created_at    timestamptz default now()
);

create table users (
  id         text primary key,
  name       text not null,
  job_title  text,
  role       text not null check (role in ('admin','equipe','leitura')),
  active     boolean default true
  -- 'pin' NÃO migra: ver §7
);

-- catálogo fixo das 19 fases (não é por coleção)
create table phases (
  id          text primary key,
  key         text unique not null,
  name        text not null,
  seq         int not null,
  marco_owner text check (marco_owner in ('anna','joice')),
  flow_type   text not null check (flow_type in ('nova','continuado','ambos'))
);

create table phase_deadlines (
  id            text primary key,
  collection_id text not null references collections(id) on delete cascade,
  phase_id      text not null references phases(id),
  deadline_date date,
  unique (collection_id, phase_id)
);

-- CRONOGRAMA MACRO: o coração do sistema
create table macro_processes (
  id            text primary key,
  collection_id text not null references collections(id) on delete cascade,
  seq           int not null,               -- número da etapa DENTRO da coleção
  name          text not null,
  macro_tema    text,                       -- Estilo | Desenvolvimento | Mostruário | Catálogo | Plano de Produção/Mostruário
  predecessores int[] default '{}',         -- seq de outras etapas DA MESMA coleção
  predecessores_editados boolean default false,
  -- LINHA DE BASE CONGELADA: nunca reescrita pela aplicação (ver §5.1)
  start_date    date,
  end_date      date,
  -- REALIZADO: digitado na plataforma
  inicio_real   date,
  fim_real      date,
  completed_at  date,                       -- espelho de fim_real (legado; unificar)
  percent_complete int default 0,
  owner_team    text,                       -- informação da planilha (equipe)
  responsavel_user_id text references users(id),   -- DONO: pessoa, não equipe
  motivo_atraso text,                       -- fornecedor|decisao|gente|retrabalho|outra_area|outro
  observacoes   text,
  created_at    timestamptz default now(),
  created_by    text references users(id),
  unique (collection_id, seq)
);

-- promessas de recuperação: APPEND-ONLY, nunca update (ver §5.6)
create table process_promises (
  id          bigserial primary key,
  process_id  text not null references macro_processes(id) on delete cascade,
  data        date not null,                -- nova data prometida
  feita_em    timestamptz not null default now(),
  feita_por   text references users(id)
);

create table references_ (          -- "references" é palavra reservada
  id            text primary key,
  collection_id text not null references collections(id) on delete cascade,
  collection_name text,             -- rótulo do time (coluna "COLEÇÃO" da grade); NÃO define a coleção
  code          text not null,
  line          text, family text, stylist text,
  flow_type     text not null check (flow_type in ('nova','continuado')),
  tipo_produto  text, tecido_principal text,
  cores         text[] default '{}',
  tamanhos      text[] default '{}',
  foto_url      text,               -- hoje é data-URL; no backend vira storage (ver §9)
  notes         text,
  status        text not null default 'ativa' check (status in ('ativa','cancelada')),
  canceled_at timestamptz, canceled_by text references users(id),
  cancel_category text, cancel_reason text,
  active        boolean default true,
  created_at    timestamptz default now(),
  created_by    text references users(id),
  unique (collection_id, code)      -- código único DENTRO da coleção
);

-- célula do grid referência × fase (ESPARSA: só existe quando houve registro)
create table reference_phases (
  id           text primary key,
  reference_id text not null references references_(id) on delete cascade,
  phase_id     text not null references phases(id),
  completed_at date,                -- espelho do último evento
  completed_by text references users(id),
  notes        text,
  unique (reference_id, phase_id)
);

-- uma fase pode ter 1ª, 2ª, 3ª ocorrência (2ª pilotagem, 2ª prova…)
create table reference_phase_events (
  id                 bigserial primary key,
  reference_phase_id text not null references reference_phases(id) on delete cascade,
  date               date not null,
  notes              text,
  by_user            text references users(id),
  at                 timestamptz default now()
);

-- governança: append-only, nunca deletar
create table reference_log (
  id        bigserial primary key,
  ref_code  text not null,
  action    text not null,          -- 'cancelamento' | 'reativacao'
  category  text, reason text,
  by_user   text references users(id),
  at        timestamptz default now()
);

create table tasks (
  id            text primary key,
  collection_id text references collections(id),   -- nulo = tarefa geral do setor
  title         text not null, description text,
  assignee_user_id text references users(id),
  ritual_id     text references rituals(id),        -- ata de origem (obrigatória na UI)
  due_date      date,
  status        text not null default 'pendente' check (status in ('pendente','em_andamento','concluida','cancelada')),
  completed_at  timestamptz,
  created_at    timestamptz default now(), created_by text references users(id)
);

create table rituals (
  id            text primary key,
  collection_id text references collections(id),
  type          text not null,      -- semanal | briefing_diario | quinzenal_interfaces | mensal_diretoria
  title         text, scheduled_at timestamptz, duration_min int,
  agenda_text   text, minutes_text text,
  minutes_published_at timestamptz,  -- meta: até 24h após scheduled_at
  created_at    timestamptz default now(), created_by text references users(id)
);

create table ritual_attendance (
  ritual_id text references rituals(id) on delete cascade,
  user_id   text references users(id),
  present   boolean default false,
  primary key (ritual_id, user_id)
);

create table kpi_entries (
  id bigserial primary key,
  kpi_key text not null,            -- 'rnc' | 'otif_mp'
  period  text not null,            -- 'YYYY-MM'
  value   numeric,
  created_at timestamptz default now(), created_by text references users(id),
  unique (kpi_key, period)
);

-- catálogos do produto: listas de NOMES (ver §5.11)
create table catalog_items (
  id   bigserial primary key,
  kind text not null check (kind in ('tipos','cores','tamanhos','tecidos')),
  name text not null,
  unique (kind, name)
);

create table bypass_log (         -- modelado, UI prevista para v2
  id bigserial primary key, collection_id text references collections(id),
  description text, at timestamptz default now(), by_user text references users(id)
);
```

**`charges`** existe no modelo atual mas a UI saiu do ar (a cobrança migrou para o Quadro de Tarefas). Decidir com o Vanderlei antes de migrar: provavelmente descartar.

## 5. As regras que não podem ser reimplementadas errado

Esta seção é a mais importante do documento. Cada regra abaixo foi definida com o cliente na reunião de 02/09/2026 (Anna, gestora, e Cairo, diretor) ou emergiu de um bug real em produção. Reimplementá-las de outro jeito quebra o produto de formas silenciosas.

### 4.1 Linha de base congelada
`start_date` / `end_date` são **a memória do que foi combinado** no início da coleção. A aplicação **nunca** os reescreve. O que o usuário grava é `inicio_real` / `fim_real`. Renegociação de prazo entra pela planilha, como decisão registrada.

> Por quê: sem isso, o time "conserta" o atraso movendo a data, o painel fica verde e a coleção continua atrasada. A comparação congelado × realizado no fim da coleção é o que calibra o cronograma do ano seguinte.

### 4.2 Etapa sem predecessor roda em paralelo
Etapa sem predecessor fica ancorada na própria data e **nunca é empurrada** por outra. Só quem tem `predecessores` herda atraso.

> É a regra que separa "atrasou, mas dá para reorganizar" de "atrasou e derrubou a cadeia". Foi pedida nestas palavras: *"o que não tem predecessor roda em paralelo; o que dá para trabalhar em paralelo não precisa empurrar"*.

### 4.3 Algoritmo de projeção (forward pass)
Para cada etapa, em dias **corridos** (é como a planilha conta):

```
se concluída (fim_real)        → projeção = datas reais, ponto final
senão se sem datas congeladas  → origem = 'indefinido' (não inventar data)
senão se SEM predecessor       → início = inicio_real || start_date     (nunca empurrada)
senão                          → início = max(fim projetado dos predecessores) + 1 dia
                                 piso: o próprio start_date (não antecipa)
                                 se inicio_real existe, ele manda
fim = início + duração congelada
se fim < hoje e não concluída  → fim = hoje        (não terminou, não pode ter terminado no passado)
```

### 4.4 Na simulação, o atraso entra DEPOIS do piso
Ao simular "e se atrasar N dias", o N é somado **depois** do clamp `fim < hoje → hoje`. Se for somado antes, o piso engole o atraso e a simulação fica inócua em toda etapa vencida — que são justamente as que importam. Este foi um bug real, pego em teste.

### 4.5 Nunca inventar data
- Sem datas congeladas → `origem: 'indefinido'`, barra tracejada na tela.
- Predecessor indefinido → `incompleto: true` e aviso de "projeção incompleta".
- Margem não calculável por falta de data → estado **`bloqueado`** ("cadeia sem data"), que é **diferente** de "fora da cadeia".
- Previsão de entrega com etapas sem data na cadeia → a tela diz **"não dá para prever"**, não mostra uma data otimista.

> Um número errado com aparência de certo é pior que a ausência dele. A diretoria decide em cima disso.

### 4.6 Promessas são append-only
Cada nova data prometida **empilha**; nunca sobrescreve a anterior. O desfecho (cumprida / quebrada / em aberto) é **derivado** comparando `fim_real` com a última promessa.

> Replanejar a mesma etapa três vezes precisa ficar visível. É o indicador "prometido × cumprido".

### 4.7 "Nada se moveu" tem três causas — e a tela precisa dizer qual
Ao simular um atraso e o resultado ser zero, a resposta deve distinguir:
1. **Nada depende dela** — o atraso fica contido.
2. **Há margem** — "só começa a empurrar a partir de N dias; a margem é de N−1 dias".
3. **A cadeia à frente passa por etapa sem data** — não dá para calcular, e diz quais etapas precisam de data.

**Checar a margem ANTES da falta de data.** A ordem inversa culpa o dado faltante quando havia folga de sobra, e manda o time atrás do problema errado. (Bug real, corrigido.)

### 4.8 Margem só conta para etapa em aberto
Uma etapa concluída não perde margem, logo não entra no contador de "sem margem de manobra".

### 4.9 Dois marcos por coleção
- `liberacao_pcp_seq` — a liberação da coleção para o PCP. Nas palavras da gestora, *"essa data é a pior de todas"*, porque está amarrada ao lead time de 60 dias de compra de matéria-prima.
- `entrega_mostruario` — o marco que a diretoria cobra.

A margem de cada etapa é medida contra esses marcos, **da coleção dela**.

### 4.10 Cada coleção é uma ilha
Etapas, datas, donos, promessas, referências, tarefas, reuniões e indicadores são **por coleção**. Nada atravessa. Em particular:
- `predecessores` são por `seq` **dentro da coleção** — ao copiar ou importar, os `seq` precisam ser **traduzidos**, nunca copiados crus.
- Chaves de preservação usam `collection_id + seq` (ou `collection_id + code`). Usar só `seq` mistura coleções — bug real.
- **A grade de referências e o cronograma da mesma planilha são a MESMA coleção.** A coluna "COLEÇÃO" da grade é rótulo do time e vive em `collection_name`, sem definir a coleção. Separá-los deixou a tela vazia em produção.

### 4.11 Catálogos guardam nomes, não ids
`tipo_produto`, `tecido_principal`, `cores[]`, `tamanhos[]` guardam o **nome**. Renomear no catálogo não quebra o cadastro de peças já feitas, e o export para Excel sai legível. Se optar por normalizar com FK no backend, **preserve esse comportamento** na API.

### 4.12 Indicadores não escondem o não-informado
O quadro "Referências por tecido principal" inclui **"— não informado —"** na base e avisa que o percentual só fecha quando todas tiverem tecido. Omitir as sem informação infla o indicador.

### 4.13 Dependência circular é barrada
Ao editar predecessores: etapas que criariam ciclo não aparecem entre as opções, e a inclusão é recusada se forçada. Sem isso a projeção entra em loop.

## 6. O que é DERIVADO (não persistir)

Calcular a cada leitura, nunca gravar:

| Derivado | Como |
|---|---|
| Status da etapa (em dia / vence em X / atrasada / concluída) | compara `end_date` e `fim_real` com hoje |
| Status da célula do grid | compara evento com `phase_deadlines` |
| Projeção (início/fim previstos) | forward pass da §5.3 |
| Margem de manobra / caminho crítico | backward pass a partir do marco da coleção |
| Cadeia de impacto ("o que empurra") | percorre sucessores |
| Desfecho da promessa | `fim_real` vs. última promessa |
| Todos os KPIs do Painel | agregações sobre os fatos |

Persistir qualquer um deles gera divergência entre telas. No front atual isso é garantido por construção: as funções de cálculo rodam a cada render.

## 7. Autenticação e permissões

**O PIN não migra.** Trocar por autenticação real — a preferência do cliente é login Google do domínio da Liebe (Supabase Auth ou equivalente).

Três papéis, já implementados na UI:

| Papel | Quem | Pode |
|---|---|---|
| `admin` | Joice, Vanderlei (PWR) | tudo, inclusive criar coleção |
| `equipe` | Anna, Camila, Thaís, Adriana, Silvana, Safira, Israel | atualizar etapas, fases, tarefas, referências |
| `leitura` | Cairo, Eugênia | só consulta (o CSS esconde elementos `.w`) |

**Aplicar as permissões no servidor (RLS).** Hoje o `leitura` é bloqueado só no cliente — basta abrir o console para contornar. Duas regras específicas de negócio:
- **Cancelar/reativar referência é exclusivo da Joice** (`canCancelRefs()`, hoje travado no id `user-joice`). É governança: toda ação entra no `reference_log`.
- **Criar coleção** é só `admin`.

## 8. Migrar os dados atuais

A fonte da verdade hoje é o navegador da Joice. **Antes de qualquer coisa, peça a ela o export JSON** (botão ⛃ Dados → "Exportar backup (JSON)"). Esse arquivo é o banco inteiro, já no schema 7.

Passos sugeridos:
1. Export JSON da máquina da Joice (e de qualquer outra que tenha sido usada).
2. Rodar as migrações do array `MIGRATIONS` se o export vier de schema anterior — ou simplesmente abrir o export no app publicado, que migra sozinho, e reexportar.
3. `INSERT` por entidade, respeitando a ordem das FKs: `users → collections → phases → phase_deadlines → macro_processes → references_ → reference_phases → reference_phase_events → o resto`.
4. Conferir os números de controle (§12).

`data.js` é gerado da planilha e serve de referência de catálogo, **não** como fonte do trabalho operacional — o realizado, os donos, promessas, fotos e catálogos só existem no navegador.

## 9. Fotos das peças

Hoje cada foto é reduzida no cliente (320 px, JPEG 0.72 ≈ 15 KB) e guardada como data-URL dentro do JSON, porque não há storage. No backend:
- Subir para um bucket (Supabase Storage / S3) e guardar a URL em `references_.foto_url`.
- **Manter a redução no cliente antes do upload** — a rede do setor é lenta e o ganho é grande (2,4 MB → 15 KB nos testes).
- Na migração, converter as data-URLs existentes em arquivos.

## 10. API — endpoints mínimos

Se usar Supabase, boa parte sai de graça via PostgREST + RLS. Se for API própria, o mínimo é:

```
GET    /collections                      lista (com resumo para a tela inicial)
POST   /collections                      cria a partir de um modelo (copia etapas/temas/predecessores, datas em aberto)
GET    /collections/:id/schedule         etapas + projeção + margem calculadas no servidor
PATCH  /processes/:id                    realizado, dono, motivo, predecessores, % avanço
POST   /processes/:id/promises           nova promessa (append-only)
GET    /processes/:id/simulate?days=N    simulação de atraso (ver §5.7)
GET    /collections/:id/references       grade
POST   /collections/:id/references       cadastro manual
PATCH  /references/:id                   dados descritivos
POST   /references/:id/cancel            só Joice; grava em reference_log
PUT    /reference-phases/:ref/:phase     registra evento de fase
GET/POST /catalog/:kind                  catálogos do produto
GET/POST /tasks · /rituals · /kpi-entries
GET    /collections/:id/agenda           pauta do ritual gerada do cronograma
```

**Onde fica o cálculo?** Recomendo **no servidor**, exposto pelo endpoint de schedule, para que web e um futuro app móvel não divirjam. O código de referência está em `index.html`, bloco "cronograma: linha de base, projeção, margem e cadeia de impacto" — é JS puro, sem dependências, portável quase 1:1.

## 11. Roteiro sugerido

1. **Banco + migração dos dados** (§3, §8) — sem isso nada mais importa.
2. **Auth + RLS** (§7) — antes de abrir para o time, senão vira bagunça de autoria.
3. **CRUD e leitura**, mantendo o front atual como cliente, se quiser validar rápido.
4. **Motor de cronograma no servidor** (§5.3–4.9) com a suíte de testes da §12.
5. **Fotos para storage** (§9).
6. **Tempo real** (subscriptions) — resolve a dor nº 2.
7. **Backlog v2** (§13).

Dá para entregar valor já no passo 1+2: o front atual consumindo a API resolve "dados por-máquina" e multiusuário, que são as duas dores maiores.

## 12. Como saber que o backend está correto

Testes de aceite que o motor atual passa — replique-os:

| Teste | Resultado esperado |
|---|---|
| Atrasar a etapa #1 em 30 dias | #5, #14 e #34 (sem predecessor) **não se movem um dia sequer** |
| Simular atraso em etapa sem sucessor (#23, #37) | "não empurra ninguém" |
| Projeção da #25 (Liberação para o PCP) na INVERNO & ALTO 27 | **+61 dias** (congelado 05/06/26, real 05/08/26) — bate com a planilha |
| Projeção da #21 (Análise de preços) | **+82 dias** |
| Etapas sem datas (#17, #28, #38, #39, #40) | `origem = 'indefinido'`, nenhuma data inventada |
| Etapa em aberto que depende de uma sem data | `incompleto = true` |
| Simular atraso em etapa já concluída | "já foi concluída, não há o que simular" |
| Simular 10 dias numa etapa com 23 de margem | "nada se move ainda; só a partir de 24 dias" |
| Contagem geral | INVERNO & ALTO 27: 40 etapas + 112 referências + 772 células · VERÃO 28: 41 etapas |

Números de controle da carga: **2 coleções com cronograma, 81 etapas macro, 112 referências, 772 células de fase, 19 fases, 15 prazos de fase, 11 usuários.**

## 13. Backlog conhecido / v2

- **Pré-custos por referência** — a aba existe na planilha, hoje quase vazia.
- **Reporte mensal à Diretoria** gerado automaticamente dos dados.
- **Taxa de Bypass** (meta ≤ 2/mês) — `bypass_log` já modelado, falta UI.
- **Multiusuário em tempo real** — o motivo principal deste handover.
- **Lacunas de dado na planilha** (não é bug de código): as etapas #17, #28, #38, #39 e #40 estão sem datas, e `38→39→40` é justamente o trecho que liga a liberação do PCP à entrega do mostruário. Enquanto estiverem vazias, a previsão de entrega não fecha. Vale cobrar do setor.
- **`charges`** — modelo órfão, decidir se remove.
- **`completed_at` × `fim_real`** — hoje espelhados por compatibilidade; unificar no backend.

---
*PWR Gestão · Vanderlei Silva · confidencial, uso interno Liebe.*
