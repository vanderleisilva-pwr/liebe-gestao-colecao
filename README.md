# Liebe · Gestão de Coleção

Sistema online de gestão do cronograma de coleção do setor de **Estilo & Produto da Liebe** (lingerie, Fortaleza/CE), operado pela **Joice (Coordenadora de Produto)**. Substitui a planilha `GESTÃO DA COLEÇÃO - INVERNO & ALTO 27.xlsx` e o caderno de anotações — é o entregável "Painel v1 / Quadro de tarefas" da Fase 1 do plano de 90 dias (projeto PWR Gestão).

**Protótipo de validação:** arquivo único HTML + JS vanilla, sem build, dados no navegador (localStorage). Após aprovação de Cairo/Joice, migra para Next.js + Supabase (ver "Migração" abaixo).

🔗 **Link online (para a Joice testar):** _será preenchido após o deploy na Vercel_
🛠️ **Manutenção (time de TI):** ver [docs/HANDOVER-TI.md](docs/HANDOVER-TI.md)

## Estrutura

| Arquivo | O que é |
|---|---|
| `index.html` | A aplicação inteira: CSS (identidade Liebe), router, store, 5 módulos, tour guiado, export/import |
| `data.js` | `window.LIEBE_SEED` — dados reais extraídos da planilha (114 referências, 35 processos, 19 fases) |
| `scripts/gerar_seed.py` | Lê o `.xlsx` e regenera `data.js`. Re-rode quando vier nova coleção: `python scripts/gerar_seed.py "caminho\do\arquivo.xlsx"` |

## Módulos

1. **Painel de Indicadores** — KPIs com meta, gatilho de alerta e responsável. Automáticos: % cumprimento do cronograma, % peças no prazo, Tempo de Piloto, Atas em 24h. Manuais (lançamento mensal): RNCs (nº absoluto) e Atraso de MP. Nomenclatura do chão de fábrica (decisão do Cairo, 12/05/2026).
2. **Cronograma Macro** — os 35 processos com status derivado ("Em dia" / "X dias em atraso" / "Concluído") + linha do tempo (Gantt) com a linha "hoje".
3. **Gestão da Coleção** — grid 114 referências × 19 fases com data-limite por fase, contadores no prazo/atraso/pendente, filtros e registro de conclusão com autoria. Fases marcadas por dono do marco: ◆ Anna (estilo) · ● Joice (prazo).
4. **Quadro de Tarefas** — kanban por pessoa (substitui o caderno).
5. **Rituais & Atas** — os 4 rituais oficiais, **pauta gerada automaticamente dos dados**, cronômetro de ata em 24h, presença e **cobranças documentadas** com evidência e escalonamento.

Tour guiado em toda página (auto na 1ª visita; botão "✦ Tour guiado" para rever).

## Acesso (protótipo)

Login client-side **apenas para registro de autoria** — não é segurança de dados. PIN padrão de todos: `1234` (editável em `data.js`). Papéis: `admin` (Joice, Vanderlei) edita tudo; `equipe` atualiza fases/tarefas; `leitura` (Cairo, Eugênia) só consulta.

## Dados & backup (importante até a migração)

- Os dados vivem no **localStorage do navegador** de cada máquina. **Convenção: a máquina da Joice é a fonte da verdade.**
- Botão **⛃ Dados** no topo: exportar backup JSON (fazer toda sexta e guardar no Drive), exportar Excel (SheetJS via CDN, com fallback CSV offline), importar backup, restaurar dados originais.
- O app avisa com banner quando o último backup tem mais de 7 dias.

## Deploy (Vercel)

Mesmo fluxo do Diagnóstico de Viabilidade: repositório GitHub (`vanderleisilva-pwr`) → vercel.com/new → import → deploy estático (sem build command, output = raiz). Sugestão de domínio: `colecao-liebe.vercel.app`.

## Migração para Next.js + Supabase (fase 2)

O modelo de dados já nasceu espelhado em tabelas: snake_case, UUIDs, FKs explícitas, datas ISO.

| Entidade no localStorage | Tabela Supabase |
|---|---|
| `users` | `users` (substituir `pin` por Supabase Auth) |
| `collections` | `collections` |
| `phases` | `phases` |
| `phase_deadlines` | `phase_deadlines` |
| `macro_processes` | `macro_processes` |
| `references` | `references` |
| `reference_phases` | `reference_phases` |
| `tasks` | `tasks` |
| `rituals` (campo `attendance` aninhado) | `rituals` + `ritual_attendance(ritual_id, user_id, present)` |
| `charges` | `charges` |
| `kpi_entries` | `kpi_entries` |
| `bypass_log` | `bypass_log` (UI prevista para v2) |

Migração = um `INSERT` por entidade lendo o export JSON. Status e KPIs nunca são armazenados (sempre derivados) — nada a migrar além dos fatos.

## V2 (fora do protótipo, modelo de dados já preparado)

Pré-custos por referência, Reporte mensal à Diretoria auto-gerado, Medidor de Taxa de Bypass (≤ 2/mês), multiusuário em tempo real (Supabase).

---
*PWR Gestão · Vanderlei Silva · jun/2026 — confidencial, uso interno Liebe.*
