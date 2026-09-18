# -*- coding: utf-8 -*-
"""
Extrai o <script> do index.html para .tmp/app.js.

Serve para checar a sintaxe sem abrir o navegador e para a suíte do motor
(scripts/teste_motor.js) carregar as funções de cálculo isoladamente.

Uso:
    python scripts/extrai_script.py
    node --check .tmp/app.js
"""
import io
import os
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / ".tmp" / "app.js"


def main():
    html = io.open(RAIZ / "index.html", encoding="utf-8", newline="").read()
    blocos = re.findall(r"<script>(.*?)</script>", html, re.S)
    if not blocos:
        raise SystemExit("Nenhum bloco <script> encontrado em index.html.")
    SAIDA.parent.mkdir(exist_ok=True)
    io.open(SAIDA, "w", encoding="utf-8", newline="").write(blocos[-1])
    print(f"OK -> {SAIDA} ({len(blocos[-1])} caracteres)")


if __name__ == "__main__":
    main()
