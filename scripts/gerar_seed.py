# -*- coding: utf-8 -*-
"""
Gera data.js (window.LIEBE_SEED) a partir da planilha real da Joice.

Uso:
    python scripts/gerar_seed.py [caminho-do-xlsx]

Por padrão lê "GESTÃO DA COLEÇÃO - INVERNO & ALTO 27.xlsx" na Área de Trabalho.
Re-rode este script quando uma nova coleção/planilha chegar.
"""
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime
from difflib import get_close_matches
from pathlib import Path

import openpyxl

XLSX_PADRAO = (
    r"C:\Users\vande\OneDrive\Pasta de Trabalho\Área de Trabalho"
    r"\GESTÃO DA COLEÇÃO - INVERNO & ALTO 27.xlsx"
)
SAIDA = Path(__file__).resolve().parent.parent / "data.js"
HOJE = "2026-06-10"  # data da geração do seed (created_at dos registros importados)
SEED_BY = "user-vanderlei"


def slug(texto):
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s.strip().lower()).strip("_")
    return s


def iso(valor):
    """Converte célula de data para 'YYYY-MM-DD' (ou None)."""
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return None


def norm(texto):
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.strip().lower())


# ---------------------------------------------------------------- usuários
# Papéis: admin = gestão total · equipe = atualiza fases/tarefas · leitura = diretoria
USERS = [
    ("user-joice", "Joice", "Coordenadora de Produto", "admin"),
    ("user-anna", "Anna Karoline", "Gerente de Estilo", "equipe"),
    ("user-thais", "Thaís", "Diretora de Estilo", "equipe"),
    ("user-adriana", "Adriana", "Modelista", "equipe"),
    ("user-silvana", "Silvana", "Pilotista Plena", "equipe"),
    ("user-safira", "Safira", "Pilotista", "equipe"),
    ("user-mariaclara", "Maria Clara", "Assistente de Estilo", "equipe"),
    ("user-israel", "Israel", "PCP", "equipe"),
    ("user-cairo", "Cairo", "Diretor Presidente", "leitura"),
    ("user-eugenia", "Eugênia", "Diretora Consultiva", "leitura"),
    ("user-vanderlei", "Vanderlei (PWR)", "Consultor PWR Gestão", "admin"),
]

# Dono do marco por fase — Regra de Ouro: criativo/técnico = Anna · prazo/processo = Joice
FASES_ANNA = {
    "desenho", "modelagem", "pilotagem", "prova", "aprov_mod",
    "pilotagem_grades", "prova_grades", "aprovacao_grade",
}

# Aplicabilidade por fluxo (a planilha só cobra fases criativas das refs novas;
# continuadas entram em cadastro de cores, liberação p/ PCP e produção de catálogo)
FASES_CONTINUADO = {"cadastro_de_cores_continuados", "liberacao_para_pcp",
                    "producao_de_peca_para_catalogo"}


def main():
    caminho = sys.argv[1] if len(sys.argv) > 1 else XLSX_PADRAO
    wb = openpyxl.load_workbook(caminho, data_only=True)

    users = [
        {"id": uid, "name": nome, "job_title": cargo, "role": papel,
         "pin": "1234", "active": True}
        for uid, nome, cargo, papel in USERS
    ]

    # ---------------------------------------------------------- Auditoria → responsáveis
    aud = wb["Auditoria"]
    resp_por_nome = {}
    for row in aud.iter_rows(min_row=6, max_row=36):
        nome = row[2].value  # col C
        resp = row[3].value  # col D
        if nome and resp:
            resp_por_nome[norm(nome)] = str(resp).strip()

    # ---------------------------------------------------------- CRONOGRAMA.V2 → processos
    cro = wb["CRONOGRAMA.V2"]
    col_id = {"INVERNO_ALTO_27": "col-inverno-alto-27"}
    macro = []
    for row in cro.iter_rows(min_row=6, max_row=41):
        seq = row[0].value  # col A
        nome = row[1].value  # col B
        if not isinstance(seq, (int, float)) or nome is None:
            continue
        nome = str(nome).strip()
        chave = norm(nome)
        resp = resp_por_nome.get(chave)
        if resp is None:
            prox = get_close_matches(chave, list(resp_por_nome), n=1, cutoff=0.6)
            resp = resp_por_nome[prox[0]] if prox else None
        pct = row[6].value  # col G (%STATUS)
        pct = round(float(pct) * 100) if isinstance(pct, (int, float)) else 0
        macro.append({
            "id": f"proc-{int(seq):02d}",
            "collection_id": col_id["INVERNO_ALTO_27"],
            "seq": int(seq),
            "name": nome,
            "owner_team": resp,            # Estilistas / Pilotagem / Assistente / PCP...
            "start_date": iso(row[3].value),   # col D (pode ser '***' → None)
            "end_date": iso(row[4].value),     # col E
            "completed_at": iso(row[5].value), # col F (CONCLUSÃO)
            "percent_complete": pct,
            "created_at": HOJE, "created_by": SEED_BY,
        })

    # ---------------------------------------------------------- GESTÃO DA COLEÇÃO
    ges = wb["GESTÃO DA COLEÇÃO"]
    # Fases = cabeçalhos da linha 8, colunas G..Y (19 fases)
    fases = []
    cols_fase = []  # (índice_coluna, phase_id)
    for cell in ges[8]:
        if cell.column < 7 or cell.column > 25:  # G=7 .. Y=25
            continue
        nome = str(cell.value).strip()
        pid = f"phase-{slug(nome)}"
        chave = slug(nome)
        fases.append({
            "id": pid,
            "key": chave,
            "name": nome,
            "seq": len(fases) + 1,
            "marco_owner": "anna" if chave in FASES_ANNA else "joice",
            "flow_type": "continuado" if chave in FASES_CONTINUADO and chave ==
                         "cadastro_de_cores_continuados" else
                         ("ambos" if chave in FASES_CONTINUADO else "nova"),
        })
        cols_fase.append((cell.column, pid))

    # Data-limite por fase (linha 2)
    deadlines = []
    for col, pid in cols_fase:
        dl = iso(ges.cell(row=2, column=col).value)
        if dl:
            deadlines.append({
                "id": f"dl-{pid[6:]}",
                "collection_id": col_id["INVERNO_ALTO_27"],
                "phase_id": pid,
                "deadline_date": dl,
            })

    # Referências (linhas 10..123) + células preenchidas
    refs, ref_phases = [], []
    colecoes_vistas = {}
    for row in ges.iter_rows(min_row=10, max_row=123):
        num = row[0].value
        if num is None:
            continue
        colecao = str(row[1].value).strip()
        if colecao not in colecoes_vistas:
            colecoes_vistas[colecao] = f"col-{slug(colecao)}"
        estilista = str(row[4].value).strip() if row[4].value else ""
        fluxo = "continuado" if "CONTINUADA" in estilista.upper() else "nova"
        rid = f"ref-{int(num):03d}"
        refs.append({
            "id": rid,
            "collection_id": colecoes_vistas[colecao],
            "collection_name": colecao,
            "code": str(row[5].value).strip(),
            "line": str(row[2].value).strip().upper(),
            "family": str(row[3].value).strip().upper(),
            "stylist": estilista,
            "flow_type": fluxo,
            "notes": str(row[25].value).strip() if row[25].value else None,  # col Z
            "active": True,
            "status": "ativa",        # 'ativa' | 'cancelada' (governança — só a Joice cancela)
            "canceled_at": None, "canceled_by": None,
            "cancel_category": None, "cancel_reason": None,
            "created_at": HOJE, "created_by": SEED_BY,
        })
        for col, pid in cols_fase:
            dt = iso(row[col - 1].value)
            if dt:
                ref_phases.append({
                    "id": f"rp-{rid[4:]}-{pid[6:]}",
                    "reference_id": rid,
                    "phase_id": pid,
                    "completed_at": dt,
                    "completed_by": "user-joice",
                    "notes": None,
                    "created_at": HOJE, "created_by": SEED_BY,
                })

    collections = [{
        "id": cid,
        "name": nome,
        "status": "em_andamento",
        "start_date": "2026-02-06",       # INICIO NOVA COLEÇÃO (CRONOGRAMA.V2)
        "end_date": "2026-12-20",         # ENTREGA MOSTRUÁRIO
    } for nome, cid in colecoes_vistas.items()]
    # garante a coleção principal mesmo sem refs
    if not any(c["id"] == col_id["INVERNO_ALTO_27"] for c in collections):
        collections.insert(0, {
            "id": col_id["INVERNO_ALTO_27"], "name": "INVERNO & ALTO 27",
            "status": "em_andamento",
            "start_date": "2026-02-06", "end_date": "2026-12-20",
        })

    # seed_version = timestamp de modificação da planilha (muda a cada nova versão
    # do .xlsx). O app compara com o que está salvo e oferece atualizar a coleção.
    seed_version = int(os.path.getmtime(caminho))
    seed = {
        "schema_version": 1,
        "seed_version": seed_version,
        "generated_at": HOJE,
        "users": users,
        "collections": collections,
        "phases": fases,
        "phase_deadlines": deadlines,
        "macro_processes": macro,
        "references": refs,
        "reference_phases": ref_phases,
        "reference_log": [],     # trilha de cancelamentos/reativações (append-only)
        "tasks": [],
        "rituals": [],
        "charges": [],
        "kpi_entries": [],
        "bypass_log": [],
    }

    js = ("// Gerado por scripts/gerar_seed.py em " + HOJE +
          " — NÃO editar à mão; re-rode o script.\n" +
          "window.LIEBE_SEED = " +
          json.dumps(seed, ensure_ascii=False, indent=1) + ";\n")
    SAIDA.write_text(js, encoding="utf-8")

    print(f"OK → {SAIDA}")
    print(f"  usuários:          {len(users)}")
    print(f"  coleções:          {len(collections)} {[c['name'] for c in collections]}")
    print(f"  fases:             {len(fases)}")
    print(f"  data-limites:      {len(deadlines)}")
    print(f"  processos macro:   {len(macro)}")
    print(f"  referências:       {len(refs)} "
          f"(novas={sum(1 for r in refs if r['flow_type']=='nova')}, "
          f"continuadas={sum(1 for r in refs if r['flow_type']=='continuado')})")
    print(f"  células de fase:   {len(ref_phases)}")
    sem_resp = [m['name'] for m in macro if not m['owner_team']]
    if sem_resp:
        print(f"  AVISO: processos sem responsável mapeado: {sem_resp}")


if __name__ == "__main__":
    main()
