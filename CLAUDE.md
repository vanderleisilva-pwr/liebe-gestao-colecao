# CLAUDE.md — Liebe · Gestão de Coleção

Orientação para agentes (Claude Code) que forem trabalhar neste repositório. **Leia antes de editar.**
Contexto de negócio e manual do usuário final: [`README.md`](README.md). Arquitetura detalhada e handover técnico: [`docs/HANDOVER-TI.md`](docs/HANDOVER-TI.md). Este arquivo não duplica os dois — foca no que é preciso para evoluir o código com segurança.

## O que é
Protótipo *single-file* de gestão do cronograma de coleção do setor de **Estilo & Produto da Liebe** (lingerie, Fortaleza/CE), operado pela **Joice** (Coordenadora de Produto). Substitui uma planilha Excel + caderno. Entregável da Fase 1 do plano de 90 dias (projeto PWR Gestão). Fase 2 planejada: migração para Next.js + Supabase.

## Comandos
```bash
# Rodar local — precisa ser via HTTP (não file://), por causa do data.js
python -m http.server 4173          # abre http://localhost:4173

# Regenerar data.js quando chegar nova planilha/coleção
pip install openpyxl                # uma vez
python scripts/gerar_seed.py "C:\caminho\GESTAO DA COLECAO ... .xlsx"
```
Sem Node, sem npm, **sem etapa de build**. Deploy: `git push` na branch `main` → a Vercel publica sozinha (estático, output = raiz; ver `vercel.json`).

## Arquitetura (o essencial)
- **Arquivo único**: a aplicação inteira vive em `index.html` — CSS no `<head>`, um `<script>` no fim. `data.js` é só o seed. Não há framework, bundler ou build. **Manter assim** salvo decisão explícita de migrar.
- **Ordem do script (não reordenar)**: `helpers → STORE → SELECTORS → ROUTER/SHELL → VIEWS → MODAIS → AÇÕES → TOUR → init`.
- **Fluxo de dados**: `window.LIEBE_SEED` (em `data.js`) → `localStorage` (chave `liebe_db`). `data.js` é **gerado** por `scripts/gerar_seed.py` a partir do `.xlsx` — **nunca editar à mão**; ajuste o script e regenere.
- **6 rotas** (hash router, objeto `ROUTES`): `#/dashboard`, `#/cronograma`, `#/colecao`, `#/tarefas`, `#/rituais`, `#/manual`.

## Convenções que NÃO podem ser quebradas
- **Toda mutação passa por `commit(fn)`** — aplica, salva (debounce) e re-renderiza, e respeita permissão de escrita. Nunca mexer no DOM e no estado em separado.
- **Status e KPIs são sempre DERIVADOS, nunca armazenados** (`statusProcesso`, `statusCelula`, `kpis`). Não persista status — calcule comparando datas com "hoje".
- **Event delegation, não listeners por elemento**: para um botão novo, dê `data-action="x"` e registre `ACTIONS['x']=(data,el,e)=>{...}`. Os handlers globais de `click/change/input/keydown` já estão no `document`.
- **Datas** sempre `'YYYY-MM-DD'`; diferença via `diffDias()` (usa `Date.UTC`, imune a fuso). Carimbo de registro via `agoraIso()`; data de hoje via `hojeStr()`.
- **Sempre `esc()`** ao interpolar dado em template string (proteção XSS).
- **Migrações de schema**: acrescente uma função ao array `MIGRATIONS`; `migrate()` cuida do incremento de `schema_version`. Mesmo padrão que irá para o Postgres na fase 2 — mantenha as migrações idempotentes.
- **`seed_version`** (timestamp do .xlsx) dispara a faixa "atualizar coleção". `applyNewSeed()` troca o catálogo (users, collections, phases, deadlines, processos, referências) e **preserva** o trabalho operacional (tarefas, atas, KPIs, cancelamentos via `reference_log`). Preserve esse contrato.

## Identidade visual — IMPORTANTE
Este é o **produto do cliente Liebe** e usa a **identidade da Liebe**, não a da PWR. Paleta em variáveis CSS no `:root` — `--rose:#b76b79`, `--cream:#faf9f5`, `--blush`, `--ink`, `--ok/--warn/--late`… Fonte **Montserrat**. **Não** aplicar as cores da PWR (laranja/azul) dentro deste app: a identidade PWR vale para entregáveis PWR (propostas, ATAs, relatórios), jamais dentro do produto do cliente. Reutilize as variáveis e os componentes existentes (`.btn`, `.card`, `.badge`, `.kpi`, `.cell`…) em vez de criar estilos avulsos.

## Domínio & permissões
- **Papéis**: `admin` (Joice, Vanderlei) edita tudo · `equipe` atualiza fases/tarefas · `leitura` (Cairo, Eugênia) só consulta (o CSS esconde os elementos `.w`). Checagens via `can('write')` / `can('admin')`.
- **Cancelar/reativar referência é exclusivo da Joice** — `canCancelRefs()` (gating por `user-joice`). Toda ação entra no `reference_log` (append-only) para governança.
- **Regra de Ouro** (visível na UI e guia decisões de produto): prazo cobra-se com a **Joice**; estilo/técnica com a **Anna**.
- **Login não é segurança** — PIN (padrão `1234`) só registra autoria. Não tratar como autenticação.
- **Idioma**: todo o código, comentários e UI são em **pt-BR**. Nomenclatura de negócio sem siglas em inglês (decisão do cliente — linguagem de "chão de fábrica"). Mantenha.

## Dados por-máquina (limite atual)
O estado vive no `localStorage` do navegador de cada máquina — **a máquina da Joice é a fonte da verdade** até a fase 2. Há export/import JSON e export Excel (SheetJS via CDN, com fallback CSV offline). O app avisa quando o último backup tem mais de 7 dias.

## Dívidas conhecidas (ao mexer perto, considere resolver)
- `README.md` está levemente defasado do código: ainda cita os marcos "◆ Anna / ● Joice" na Gestão da Coleção e o KPI "Peças no Prazo", ambos já removidos. Atualizar quando editar as áreas relacionadas.
- Modelo `charges` e funções `mCharge` / `charge-save` / `charge-status` continuam no `index.html`, mas a UI de cobrança saiu dos Rituais (migrou para o Quadro de Tarefas). A aba "Cobranças" ainda é gerada no export Excel. Decidir: remover de vez ou reaproveitar.
- Backlog v2 (ver `HANDOVER-TI.md` §8): pré-custos por referência, reporte mensal à Diretoria auto-gerado, medidor de Taxa de Bypass (`bypass_log` já modelado), multiusuário em tempo real.

## Dependências externas (CDN)
Apenas Google Fonts (Montserrat) e SheetJS (xlsx, carregado sob demanda no momento do export). Todo o resto é self-contained. Não introduzir novas dependências sem necessidade real e clara.

## Fluxo de trabalho com o agente
1. Editar `index.html` (ou `scripts/gerar_seed.py` + regenerar `data.js`).
2. Validar rodando local (`python -m http.server 4173`) e conferir no navegador.
3. Commit descritivo em pt-BR. Push na `main` publica na Vercel automaticamente.
4. Só fazer commit/push quando o Vanderlei aprovar.
