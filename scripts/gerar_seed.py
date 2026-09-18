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

# Onde procurar a planilha quando nenhum caminho vem na linha de comando.
# 1º a pasta "planilhas/" do próprio projeto (funciona em qualquer máquina);
# 2º a Área de Trabalho do autor original, por compatibilidade.
PASTA_PLANILHAS = Path(__file__).resolve().parent.parent / "planilhas"
XLSX_FALLBACK = (
    r"C:\Users\vande\OneDrive\Pasta de Trabalho\Área de Trabalho"
    r"\GESTÃO DA COLEÇÃO - INVERNO & ALTO 27.xlsx"
)


def xlsx_padrao():
    """A planilha principal é a que tem a aba CRONOGRAMA.V2 (grade + cronograma)."""
    if PASTA_PLANILHAS.is_dir():
        for arq in sorted(PASTA_PLANILHAS.glob("*.xlsx")):
            try:
                if "CRONOGRAMA.V2" in openpyxl.load_workbook(arq, read_only=True).sheetnames:
                    return str(arq)
            except Exception:
                continue
    return XLSX_FALLBACK
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


# ---------------------------------------------------------------- planilha
# A planilha é editada pelo cliente: colunas e linhas já foram inseridas no meio
# (a reunião de 02/09 acrescentou "Macro Tema" e "Predecessor"). Por isso nada
# aqui é lido por posição fixa — cabeçalho e coluna são localizados pelo NOME.
def achar_linha(ws, coluna, texto, limite=30):
    """Número da linha cujo valor na `coluna` bate com `texto` (ou None)."""
    alvo = norm(texto)
    for r in range(1, limite + 1):
        v = ws.cell(row=r, column=coluna).value
        if v is not None and norm(v) == alvo:
            return r
    return None


def mapa_colunas(ws, linha):
    """{cabeçalho normalizado: índice 0-based} da linha de cabeçalho informada."""
    m = {}
    for c in range(1, ws.max_column + 1):
        v = ws.cell(row=linha, column=c).value
        if v is not None and str(v).strip():
            m.setdefault(norm(v), c - 1)
    return m


def parse_predecessores(valor):
    """'6, 7 e 15' -> [6, 7, 15]. Texto livre em pt-BR: tolera 'e', vírgula e espaços."""
    if valor is None:
        return []
    saida = []
    for n in re.findall(r"\d+", str(valor)):
        i = int(n)
        if i not in saida:
            saida.append(i)
    return saida


def ler_marcos(cro):
    """Datas mestras no cabeçalho da CRONOGRAMA.V2 (rótulo na col. B, data na col. C)."""
    m = {}
    for r in range(1, 6):
        rot, val = cro.cell(row=r, column=2).value, iso(cro.cell(row=r, column=3).value)
        if not rot or not val:
            continue
        k = norm(rot)
        if "entrega" in k:                       # "ENTREGA MONSTRUÁRIO" (sic, na planilha)
            m["entrega_mostruario"] = val
        elif "inicio" in k:
            m["inicio_nova_colecao"] = val   # próxima coleção, não a atual
        elif "fim" in k and "anterior" in k:
            m["fim_colecao_anterior"] = val
    return m


def usuario_por_nome(valor):
    """Nome na planilha -> id do usuário cadastrado (ou None). Só aceita match claro."""
    if not valor:
        return None
    alvo = norm(valor)
    for uid, nome, _cargo, _papel in USERS:
        n = norm(nome)
        if alvo == n or alvo == n.split(" ")[0] or n.startswith(alvo):
            return uid
    return None


def macro_tema(seq, valor):
    """Macro tema da planilha, com 'Criação' dividida conforme pedido do Cairo (02/09):
    o que depende da estilista = Estilo; o que depende de fornecedor/execução = Desenvolvimento."""
    tema = str(valor).strip() if valor else None
    if not tema:
        return None
    if norm(tema) == "criacao":
        return "Desenvolvimento" if seq in CRIACAO_DESENVOLVIMENTO else "Estilo"
    return tema


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

# Itens de "Criação" que são execução técnica / cadeia de fornecimento e não
# decisão de estilo — viram macro tema "Desenvolvimento" (os demais, "Estilo").
CRIACAO_DESENVOLVIMENTO = {4, 6, 7, 9, 24}

# Aplicabilidade por fluxo (a planilha só cobra fases criativas das refs novas;
# continuadas entram em cadastro de cores, liberação p/ PCP e produção de catálogo)
FASES_CONTINUADO = {"cadastro_de_cores_continuados", "liberacao_para_pcp",
                    "producao_de_peca_para_catalogo"}

# ---------------------------------------------------------------- coleções adicionais
# Planilha de cronograma "simples": Processo | DATA INICIAL | DATA FINAL | INICIO | FINAL
# (as duas primeiras datas são a linha de base congelada; as duas últimas, o realizado).
# Ela NÃO traz macro tema nem predecessor — esses são herdados do catálogo da coleção
# modelo, casando pelo nome do processo. É assim que a governança atravessa coleções
# sem que os dados se misturem: cada coleção tem suas próprias etapas e datas.
def ler_colecao_extra(caminho, catalogo, seq_pcp_modelo):
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb[wb.sheetnames[0]]

    lin_cab = achar_linha(ws, 1, "Processo")
    if lin_cab is None:
        raise SystemExit(f"{caminho}: cabeçalho 'Processo' não encontrado na coluna A.")
    cols = mapa_colunas(ws, lin_cab)

    def c(*nomes):
        for n in nomes:
            if n in cols:
                return cols[n]
        return None

    C_NOME = c("processo")
    C_INI, C_FIM = c("data inicial", "inicio previsto"), c("data final", "fim previsto")
    C_RINI, C_RFIM = c("inicio"), c("final")

    nome_colecao = str(ws.cell(1, 1).value or "").strip()
    nome_colecao = re.sub(r"^CRONOGRAMA\s+(PRODUTO\s*-\s*)?", "", nome_colecao, flags=re.I).strip() or "NOVA COLEÇÃO"
    cid = "col-" + slug(nome_colecao)

    # catálogo por nome normalizado, para herdar macro tema / predecessores / equipe
    por_nome = {norm(p["name"]): p for p in catalogo}
    usados, linhas = set(), []
    for row in ws.iter_rows(min_row=lin_cab + 1, max_row=ws.max_row):
        nome = row[C_NOME].value if C_NOME is not None and C_NOME < len(row) else None
        if not nome:
            continue
        nome = str(nome).strip()
        ini, fim = iso(row[C_INI].value) if C_INI is not None else None, iso(row[C_FIM].value) if C_FIM is not None else None
        if not ini and not fim:
            continue  # linhas de anotação no rodapé da planilha
        modelo = por_nome.get(norm(nome))
        if modelo is None:
            prox = get_close_matches(norm(nome), list(por_nome), n=1, cutoff=0.72)
            modelo = por_nome[prox[0]] if prox else None
        if modelo is not None:
            usados.add(modelo["seq"])
        linhas.append({
            "name": nome,
            "start_date": ini,
            "end_date": fim,
            "inicio_real": iso(row[C_RINI].value) if C_RINI is not None and C_RINI < len(row) else None,
            "fim_real": iso(row[C_RFIM].value) if C_RFIM is not None and C_RFIM < len(row) else None,
            "modelo": modelo,
        })

    # Etapas do catálogo que NÃO vieram na planilha entram assim mesmo, com datas em
    # aberto: o time preenche na plataforma. Sem elas a cadeia de dependências quebra.
    faltantes = [p for p in catalogo if p["seq"] not in usados]

    # ordena pelo seq do modelo; o que é novo vai para o fim, preservando a ordem da planilha
    com_modelo = [l for l in linhas if l["modelo"]]
    sem_modelo = [l for l in linhas if not l["modelo"]]
    com_modelo.sort(key=lambda l: l["modelo"]["seq"])

    procs, seq = [], 0
    mapa_seq = {}  # seq no modelo -> seq nesta coleção (para reescrever os predecessores)

    def add(nome, ini, fim, rini, rfim, modelo):
        nonlocal seq
        seq += 1
        if modelo:
            mapa_seq[modelo["seq"]] = seq
        procs.append({
            "id": f"{cid}-proc-{seq:02d}", "collection_id": cid, "seq": seq, "name": nome,
            "owner_team": (modelo or {}).get("owner_team"),
            "responsavel_user_id": None, "motivo_atraso": None, "promessas": [],
            "macro_tema": (modelo or {}).get("macro_tema"),
            "predecessores": [],  # preenchido no segundo passe, já com os seq desta coleção
            "_pred_modelo": (modelo or {}).get("predecessores", []),
            "start_date": ini, "end_date": fim,
            "inicio_real": rini, "fim_real": rfim, "completed_at": rfim,
            "percent_complete": 100 if rfim else 0,
            "observacoes": None if modelo else "Etapa nova nesta coleção — sem equivalente no catálogo.",
            "created_at": HOJE, "created_by": SEED_BY,
        })

    for l in com_modelo:
        add(l["name"], l["start_date"], l["end_date"], l["inicio_real"], l["fim_real"], l["modelo"])
    for p in faltantes:
        add(p["name"], None, None, None, None, p)   # datas em aberto, para preencher
    for l in sem_modelo:
        add(l["name"], l["start_date"], l["end_date"], l["inicio_real"], l["fim_real"], None)

    # segundo passe: traduz os predecessores do catálogo para os seq desta coleção
    for p in procs:
        p["predecessores"] = [mapa_seq[s] for s in p.pop("_pred_modelo") if s in mapa_seq]

    datas = sorted(d for p in procs for d in (p["start_date"], p["end_date"]) if d)
    colecao = {
        "id": cid, "name": nome_colecao, "status": "em_andamento",
        "start_date": datas[0] if datas else None,
        "end_date": datas[-1] if datas else None,
        "marcos": {
            "entrega_mostruario": datas[-1] if datas else None,
            "liberacao_pcp_seq": mapa_seq.get(seq_pcp_modelo),
        },
    }
    return colecao, procs, len(faltantes), len(sem_modelo)


def main():
    args = sys.argv[1:]
    # planilhas de coleções adicionais (só cronograma): --colecao "caminho.xlsx"
    extras = [args[i + 1] for i, a in enumerate(args) if a == "--colecao" and i + 1 < len(args)]
    # o caminho da principal é o primeiro argumento solto (nem flag, nem valor de flag)
    consumidos = {i for i, a in enumerate(args) if a == "--colecao"}
    consumidos |= {i + 1 for i in consumidos}
    soltos = [a for i, a in enumerate(args) if i not in consumidos and not a.startswith("--")]
    caminho = soltos[0] if soltos else xlsx_padrao()
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
    marcos = ler_marcos(cro)
    lin_cab = achar_linha(cro, 2, "Processo")
    if lin_cab is None:
        raise SystemExit("CRONOGRAMA.V2: cabeçalho 'Processo' não encontrado na coluna B.")
    cols = mapa_colunas(cro, lin_cab)

    def c(nome, obrigatoria=True):
        if nome in cols:
            return cols[nome]
        if obrigatoria:
            raise SystemExit(f"CRONOGRAMA.V2: coluna '{nome}' não encontrada na linha {lin_cab}.")
        return None

    C_NOME, C_RESP = c("processo"), c("responsavel", False)
    C_TEMA, C_PRED = c("macro tema"), c("predecessor")
    C_INI, C_FIM = c("inicio"), c("final")
    C_CONCL, C_PCT = c("conclusao"), c("%status")
    C_OBS = c("observacoes", False)

    def val(row, idx):
        return row[idx].value if idx is not None and idx < len(row) else None

    macro = []
    for row in cro.iter_rows(min_row=lin_cab + 1, max_row=cro.max_row):
        seq = row[0].value  # col A
        nome = val(row, C_NOME)
        if not isinstance(seq, (int, float)) or nome is None:
            continue
        seq = int(seq)
        nome = str(nome).strip()
        chave = norm(nome)
        # Responsável: a coluna da planilha manda; senão, casa pelo nome na aba Auditoria.
        resp = str(val(row, C_RESP)).strip() if val(row, C_RESP) else None
        if not resp:
            resp = resp_por_nome.get(chave)
            if resp is None:
                # cutoff alto de propósito: num sistema de cobrança de prazo, responsável
                # ERRADO é pior que responsável vazio. O certo é preencher a coluna
                # "Responsável" na planilha — o AVISO no fim do script lista quem falta.
                prox = get_close_matches(chave, list(resp_por_nome), n=1, cutoff=0.9)
                resp = resp_por_nome[prox[0]] if prox else None
        pct = val(row, C_PCT)
        pct = round(float(pct) * 100) if isinstance(pct, (int, float)) else 0
        obs = str(val(row, C_OBS)).strip() if val(row, C_OBS) else None
        concl = iso(val(row, C_CONCL))
        macro.append({
            "id": f"proc-{seq:02d}",
            "collection_id": col_id["INVERNO_ALTO_27"],
            "seq": seq,
            "name": nome,
            "owner_team": resp,
            # Dono por PESSOA: equipe não entrega, pessoa entrega. Só preenche quando
            # a planilha nomeia alguém do cadastro; senão fica para atribuir na plataforma.
            "responsavel_user_id": usuario_por_nome(val(row, C_RESP)),
            "motivo_atraso": None,
            "promessas": [],
            "macro_tema": macro_tema(seq, val(row, C_TEMA)),
            "predecessores": parse_predecessores(val(row, C_PRED)),
            # start_date/end_date = LINHA DE BASE CONGELADA: nunca alteradas pela tela.
            "start_date": iso(val(row, C_INI)),
            "end_date": iso(val(row, C_FIM)),
            # realizado: a planilha traz o que já aconteceu; daqui em diante é a plataforma.
            "inicio_real": None,
            "fim_real": concl,
            "completed_at": concl,
            "percent_complete": pct,
            "observacoes": obs,
            "created_at": HOJE, "created_by": SEED_BY,
        })

    # ---------------------------------------------------------- GESTÃO DA COLEÇÃO
    ges = wb["GESTÃO DA COLEÇÃO"]
    # Fases = cabeçalhos da linha do "#", colunas G..Y (19 fases).
    # A linha é localizada pelo nome porque a planilha já ganhou linhas no topo.
    lin_refs = achar_linha(ges, 1, "#")
    if lin_refs is None:
        raise SystemExit("GESTÃO DA COLEÇÃO: cabeçalho '#' não encontrado na coluna A.")
    fases = []
    cols_fase = []  # (índice_coluna, phase_id)
    for cell in ges[lin_refs]:
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

    # Referências (tudo abaixo do cabeçalho) + células preenchidas
    refs, ref_phases = [], []
    colecoes_vistas = {}
    for row in ges.iter_rows(min_row=lin_refs + 1, max_row=ges.max_row):
        num = row[0].value
        if num is None:
            continue
        # A coluna "COLEÇÃO" da grade é um rótulo do time (ex.: "INVERNO 27"), não
        # uma coleção separada: a grade e o cronograma vêm da MESMA planilha e são a
        # mesma coleção. O rótulo fica em collection_name, para filtro e conferência.
        colecao = str(row[1].value).strip()
        colecoes_vistas[colecao] = colecoes_vistas.get(colecao, 0) + 1
        estilista = str(row[4].value).strip() if row[4].value else ""
        fluxo = "continuado" if "CONTINUADA" in estilista.upper() else "nova"
        rid = f"ref-{int(num):03d}"
        refs.append({
            "id": rid,
            "collection_id": col_id["INVERNO_ALTO_27"],
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

    # Datas mestras: o cabeçalho da planilha manda; os defaults são a coleção atual.
    inicio_colecao = min((p["start_date"] for p in macro if p["start_date"]), default="2026-02-06")
    entrega_mostruario = marcos.get("entrega_mostruario", "2026-12-20")
    # Marco que a gestora apontou como "a pior data de todas" (lead time de compra).
    seq_pcp = next((p["seq"] for p in macro
                    if "pcp" in norm(p["name"]) and "libera" in norm(p["name"])), None)

    collections = [{
        "id": col_id["INVERNO_ALTO_27"], "name": "INVERNO & ALTO 27",
        "status": "em_andamento",
        "start_date": inicio_colecao,     # INICIO NOVA COLEÇÃO (CRONOGRAMA.V2)
        "end_date": entrega_mostruario,   # ENTREGA MOSTRUÁRIO (CRONOGRAMA.V2)
        "marcos": {**marcos, "entrega_mostruario": entrega_mostruario,
                   "liberacao_pcp_seq": seq_pcp},
    }]

    # ---------------------------------------------------------- coleções adicionais
    # Cada uma entra 100% separada: etapas, datas, marcos e governança próprios.
    macro_extra, resumo_extra = [], []
    for cx in extras:
        col_x, procs_x, n_falt, n_novos = ler_colecao_extra(cx, macro, seq_pcp)
        collections = [c for c in collections if c["id"] != col_x["id"]] + [col_x]
        macro_extra += procs_x
        resumo_extra.append((col_x["name"], len(procs_x), n_falt, n_novos))
    macro = macro + macro_extra

    # seed_version = timestamp de modificação da planilha (muda a cada nova versão
    # do .xlsx). O app compara com o que está salvo e oferece atualizar a coleção.
    # Considera TODAS as planilhas: se só olhasse a principal, acrescentar uma
    # coleção nova não avisaria ninguém que já tinha aplicado a versão anterior.
    seed_version = max(int(os.path.getmtime(c)) for c in [caminho] + extras)
    seed = {
        "schema_version": 1,
        "seed_version": seed_version,
        "generated_at": HOJE,
        "marcos": {**marcos, "liberacao_pcp_seq": seq_pcp},
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
    # newline="" mantém LF também no Windows: sem isso o data.js inteiro
    # aparece como modificado a cada regeneração e o diff real some.
    SAIDA.write_text(js, encoding="utf-8", newline="")

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
    for nome_x, n_x, n_falt, n_novos in resumo_extra:
        print(f"  + coleção {nome_x}: {n_x} etapas "
              f"({n_falt} sem datas para preencher na plataforma, {n_novos} nova(s) nesta coleção)")
    sem_resp = [m['name'] for m in macro if not m['owner_team']]
    if sem_resp:
        print(f"  AVISO: processos sem responsável mapeado: {sem_resp}")


if __name__ == "__main__":
    main()
