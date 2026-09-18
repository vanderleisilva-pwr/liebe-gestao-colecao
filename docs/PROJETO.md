# Dossiê do Projeto — Liebe · Gestão de Coleção

> Documento-mãe de conhecimento do projeto. Consolida contexto, pessoas, decisões e estado atual para **retomar o trabalho a qualquer momento e em qualquer computador**. Preserva o raciocínio que, de outra forma, viveria só nas mensagens de commit e na memória local.
>
> **Mapa de documentos:** visão geral e manual → [`README.md`](../README.md) · convenções de código para agentes → [`CLAUDE.md`](../CLAUDE.md) · handover técnico para o TI da Liebe → [`HANDOVER-TI.md`](HANDOVER-TI.md) · este arquivo = contexto + histórico + retomada.

---

## 1. Contexto e propósito

Sistema online de gestão do cronograma de coleção do setor de **Estilo & Produto da Liebe** (lingerie, Fortaleza/CE). Substitui a planilha `GESTÃO DA COLEÇÃO - INVERNO & ALTO 27.xlsx` e o caderno de anotações da operação.

- **Cliente:** Liebe (lingerie).
- **Consultoria:** PWR Gestão — Vanderlei Silva.
- **Operadora principal:** Joice (Coordenadora de Produto).
- **Onde entra:** entregável "Painel v1 / Quadro de tarefas" da **Fase 1 do plano de 90 dias** (projeto PWR Gestão).
- **Natureza:** protótipo de validação em produção (uso interno). Após aprovação de Cairo/Joice, migra para **Next.js + Supabase** (Fase 2).

## 2. Pessoas & papéis (login do protótipo)

Papéis no app: `admin` edita tudo · `equipe` atualiza fases/tarefas · `leitura` só consulta. PIN padrão `1234` (só registra autoria — **não** é segurança).

| Pessoa | Cargo | Papel |
|---|---|---|
| Joice | Coordenadora de Produto | admin |
| Vanderlei (PWR) | Consultor PWR Gestão | admin |
| Anna Karoline | Gerente de Estilo | equipe |
| Thaís | Diretora de Estilo | equipe |
| Adriana | Modelista | equipe |
| Silvana | Pilotista Plena | equipe |
| Safira | Pilotista | equipe |
| Maria Clara | Assistente de Estilo | equipe |
| Israel | PCP | equipe |
| Cairo | Diretor Presidente | leitura |
| Eugênia | Diretora Consultiva | leitura |

## 3. Arquitetura em 30 segundos

Site estático de **arquivo único** (`index.html`), HTML+CSS+JS **vanilla**, **sem build**, **sem backend**. Estado no `localStorage`. Seed de dados em `data.js` (gerado da planilha por `scripts/gerar_seed.py`). Deploy estático na Vercel. Detalhe de convenções em [`CLAUDE.md`](../CLAUDE.md); anatomia do código e stack em [`HANDOVER-TI.md`](HANDOVER-TI.md) §2–§3.

## 4. Dados da coleção (números do seed atual)

Seed gerado em **2026-06-10** a partir da planilha. Coleção única: **INVERNO & ALTO 27** (início 2026-02-06 → entrega mostruário 2026-12-20).

- **11** usuários · **19** fases · **35** processos macro · **~114** referências (novas + continuadas).
- Modelo de dados já espelha tabelas relacionais (snake_case, UUIDs, FKs, datas ISO) → migração para Supabase é 1 `INSERT` por entidade. Mapa completo em [`HANDOVER-TI.md`](HANDOVER-TI.md) §7.

## 5. Módulos (5 páginas + Manual)

1. **Painel de Indicadores** — KPIs com meta, gatilho de alerta e responsável (automáticos + manuais).
2. **Cronograma Macro** — um cronograma por coleção, 100% isolado (etapas, datas, donos, promessas e indicadores próprios), com assistente para criar novas coleções a partir de um modelo. Processos com macro tema e predecessores; prazo congelado x realizado/previsto, margem de manobra, simulação de atraso e linha do tempo com zoom mês/semana/dia. Governança: dono por pessoa, data prometida de recuperação (com placar prometido x cumprido), motivo do atraso e filtro "precisa de atenção".
3. **Gestão da Coleção** — grid de referências × 19 fases da coleção selecionada, com **cadastro e edição de referências direto na plataforma** (tipo de produto, tecido principal, cores, tamanhos e foto da peça), data-limite por fase, filtros, conclusão com autoria e cancelamento governado.
4. **Quadro de Tarefas** — kanban por pessoa (substitui o caderno; card exige ata de origem).
5. **Rituais & Atas** — os 4 rituais oficiais, pauta gerada dos dados, cronômetro de ata em 24h, presença.
6. **Manual de Uso** — documentação embutida no app.

Tour guiado em toda página (automático na 1ª visita).

## 6. Decisões-chave e histórico (o "porquê")

Evolução do protótipo, do primeiro commit ao atual (o raciocínio por trás de cada mudança):

1. **v1** — painel, cronograma, grid, tarefas, rituais + tour guiado.
2. **UX de navegação** — sidebar fixa com nav rolável + Manual de Uso completo + detecção de nova versão da planilha; depois menu lateral recolhível (burger).
3. **Publicação & handover** — `.gitignore`, `README.md`, `docs/HANDOVER-TI.md`, `vercel.json` (deploy estático, headers noindex/segurança).
4. **Governança de referências** — cancelamento com justificativa + categoria + histórico append-only (`reference_log`); **exclusivo da Joice** (`canCancelRefs()`).
5. **Fases com múltiplos eventos datados** — uma fase pode ter 1ª, 2ª, 3ª ocorrência por referência.
6. **Revisão do Painel** — "Cumprimento do Cronograma" passou a ser *realizado vs. previsto*; "Tempo de Pilotagem" medido de desenho→pilotagem; KPI "Peças no Prazo" removido.
7. **Simplificação de responsabilidade** — removidos os marcos "◆ Anna / ● Joice" da Gestão da Coleção: **todo o cronograma é responsabilidade da Joice**.
8. **Tarefas** — ata de origem obrigatória no card + filtros de prazo e de ata.
9. **Cobranças** — removidas dos Rituais; a gestão de cobrança migrou para o **Quadro de Tarefas**.

Decisões de negócio que orientam o produto:
- **Nomenclatura de "chão de fábrica"**, em pt-BR e sem siglas em inglês (decisão do Cairo, 12/05/2026).
- **Regra de Ouro**: prazo cobra-se com a **Joice**; estilo/técnica com a **Anna**.
- **Cancelar/reativar referência** é ação exclusiva da Joice, sempre registrada.
- **Login é só autoria**, não autenticação.

## 7. Estado atual (jul/2026)

- **Em produção** na Vercel (uso interno), como protótipo de validação. Aguardando aprovação de Cairo/Joice para iniciar a Fase 2.
- **Último commit de código:** `98211f3` — "Remove cobranças dos Rituais".
- **Repositório:** https://github.com/vanderleisilva-pwr/liebe-gestao-colecao (privado).
- **Deploy:** https://liebe-gestao-colecao.vercel.app
- **Dívidas conhecidas** (ver [`CLAUDE.md`](../CLAUDE.md) → "Dívidas conhecidas"): README levemente defasado; modelo/funções `charges` órfãos após a migração da cobrança para Tarefas.

## 8. Backlog / próximos passos

**Fase 2 — Next.js + Supabase** (mapa de migração pronto no HANDOVER §7): resolve o limite "dados por-máquina", traz multiusuário em tempo real e Auth real (trocar PIN por login Google do domínio).

**Recursos v2** (modelo de dados já preparado):
- Pré-custos por referência.
- Reporte mensal à Diretoria gerado automaticamente dos dados.
- Medidor de Taxa de Bypass (≤ 2/mês) — `bypass_log` já modelado.

**Melhorias a definir (próxima sessão):** _reservado para as melhorias que o Vanderlei irá detalhar — registrar aqui quando forem priorizadas._

## 9. Como retomar em um computador novo

1. **Instalar** Git (obrigatório) e, se for regenerar o seed, Python 3 + `pip install openpyxl`.
2. **Autenticar no GitHub** (login no navegador na 1ª vez que o Git pedir credenciais, via Git Credential Manager).
3. **Clonar:**
   ```bash
   git clone https://github.com/vanderleisilva-pwr/liebe-gestao-colecao.git
   ```
4. **Abrir a pasta no Claude Code** e pedir para ele ler `CLAUDE.md` e `docs/PROJETO.md` — todo o contexto será reconstituído a partir daí.
5. **Rodar local:** `python -m http.server 4173` → http://localhost:4173
6. **Deploy:** segue automático — a conta da **Vercel já está conectada a este repositório**; cada `push` na `main` publica sozinho. Nada a reconfigurar.

**Atenção — memória local do Claude Code:** as memórias ficam em `C:\Users\vande\.claude\` e **serão apagadas na formatação**. O conhecimento essencial do projeto está preservado neste repositório (README + CLAUDE.md + este dossiê). Se quiser preservar também as memórias do Claude (que incluem outros contextos além deste projeto), copie a pasta `C:\Users\vande\.claude` para um backup externo (Drive/pendrive) antes de formatar.

---
*PWR Gestão · Vanderlei Silva · confidencial, uso interno Liebe.*
