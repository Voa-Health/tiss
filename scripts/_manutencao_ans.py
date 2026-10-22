"""Preparação de dados públicos da ANS."""

from __future__ import annotations

import datetime
import io
import json
import posixpath
import re
import unicodedata
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

if __package__:
    from ._manutencao_common import read_csv, write_json
else:
    from _manutencao_common import read_csv, write_json

ROOT = Path(__file__).resolve().parents[1]
DOMAIN_OUT = ROOT / "src/voa_tiss/_data/domain.json"
HEALTHPLANS_OUT = ROOT / "src/voa_tiss/_data/healthplans.json"
GLOSA_OUT = ROOT / "src/voa_tiss/_data/glosas.json"
GLOSA_DOMAIN = DOMAIN_OUT

PDA_URL = (
    "https://dadosabertos.ans.gov.br/FTP/PDA/"
    "terminologia_unificada_saude_suplementar_TUSS-049/pda-049-tuss.zip"
)

CADOP_URL = (
    "https://dadosabertos.ans.gov.br/FTP/PDA/"
    "operadoras_de_plano_de_saude_ativas/Relatorio_cadop.csv"
)

TABELA38_URL = (
    "https://www.ans.gov.br/arquivos/extras/tiss/"
    "Padrao_TISS_Representacao_de_Conceitos_em_Saude_202609.zip"
)

DOMAIN_TABLES = {
    "23",
    "24",
    "36",
    "39",
    "41",
    "43",
    "50",
    "52",
    "57",
    "60",
    "63",
    "76",
    "77",
}

DOMAIN_SOURCE = (
    "ANS, TISS/RPS: "
    "https://dadosabertos.ans.gov.br/FTP/PDA/terminologia_unificada_saude_suplementar_TUSS-049/pda-049-tuss.zip"
)

CADOP_SOURCE = (
    "ANS, Relatório CADOP: "
    "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/Relatorio_cadop.csv"
)

_DOMINIOS_GENERICOS = {
    "gmail.com",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "msn.com",
    "icloud.com",
    "yahoo.com",
    "yahoo.com.br",
    "uol.com.br",
    "bol.com.br",
    "terra.com.br",
    "ig.com.br",
    "aol.com",
    "globo.com",
    "globomail.com",
    "gmail.com.br",
    "hotmail.com.br",
    "infonet.com.br",
    "live.com.br",
    "me.com",
    "netsite.com.br",
    "outlook.com.br",
    "passosnet.com.br",
    "proton.me",
    "protonmail.com",
    "r7.com",
    "uol.com",
    "yahoo.com.ar",
    "zipmail.com.br",
}


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").upper()


def _table_id(path: str) -> str | None:
    match = re.search(r"tabela[_ ](\d+)", path.casefold())
    return match.group(1) if match else None


def bake_domain(archive: Path) -> dict[str, Any]:
    records: list[dict[str, str]] = []
    table_names: dict[str, str] = {}
    with zipfile.ZipFile(archive) as bundle:
        for name in sorted(bundle.namelist()):
            table = _table_id(name)
            if table not in DOMAIN_TABLES or not name.casefold().endswith(".csv"):
                continue
            rows = read_csv(bundle.read(name))
            if not rows:
                continue
            fields = {_fold(field): field for field in rows[0]}
            code_column = fields.get("CD_TERMO") or fields.get("CODIGO")
            term_column = (
                fields.get("NM_TERMO")
                or fields.get("TERMO")
                or fields.get("DS_TERMO_DETALHADO")
                or fields.get("DS_TERMO_DETALHADA")
            )
            description_column = (
                fields.get("DS_TERMO_DETALHADO")
                or fields.get("DS_TERMO_DETALHADA")
                or fields.get("DS_TERMO")
                or term_column
            )
            if not code_column or not term_column:
                raise ValueError(f"Colunas de código/termo ausentes em {name}: {rows[0].keys()}")
            table_names[table] = re.sub(r"^pda-\d+-", "", Path(name).stem).replace("_", " ")
            for row in rows:
                code = row.get(code_column, "")
                term = row.get(term_column, "")
                if not code or not term:
                    continue
                records.append(
                    {
                        "tabela": table,
                        "codigo": code,
                        "termo": term,
                        "descricao": row.get(description_column, "") or term,
                        "vigencia_inicio": row.get(fields.get("DT_INICIO_VIGENCIA", ""), ""),
                        "vigencia_fim": row.get(fields.get("DT_FIM_VIGENCIA", ""), ""),
                    }
                )
    records.sort(key=lambda row: (int(row["tabela"]), row["codigo"], row["termo"]))
    return {
        "version": 1,
        "source": DOMAIN_SOURCE,
        "license": "não informado",
        "tables": table_names,
        "table_info": [
            [table, table_names[table], sum(row["tabela"] == table for row in records)]
            for table in sorted(table_names, key=int)
        ],
        "records_count": len(records),
        "records": records,
    }


def bake_healthplans(source: Path) -> dict[str, Any]:
    raw = source.read_bytes()
    rows = read_csv(raw)
    records = {}
    domains: dict[str, set[str]] = {}
    for row in rows:
        registro = (row.get("REGISTRO_OPERADORA") or "").strip()
        if not registro:
            continue
        records[registro] = {
            "registro_ans": registro,
            "cnpj": (row.get("CNPJ") or "").strip(),
            "razao_social": (row.get("RAZAO_SOCIAL") or "").strip(),
            "nome_fantasia": (row.get("NOME_FANTASIA") or "").strip(),
            "modalidade": (row.get("MODALIDADE") or "").strip(),
            "cidade": (row.get("CIDADE") or "").strip(),
            "uf": (row.get("UF") or "").strip(),
            "data_registro_ans": (row.get("DATA_REGISTRO_ANS") or "").strip(),
        }
        email = (row.get("ENDERECO_ELETRONICO") or "").strip().lower()
        domain = email.rsplit("@", 1)[-1] if "@" in email else ""
        if domain not in _DOMINIOS_GENERICOS and re.fullmatch(
            r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", domain
        ):
            domains.setdefault(domain, set()).add(registro)
    return {
        "version": 1,
        "source": CADOP_SOURCE,
        "license": "CC BY",
        "records": dict(sorted(records.items())),
        "dominios": {domain: sorted(registros) for domain, registros in sorted(domains.items())},
    }


SOURCE_URL = (
    "https://www.ans.gov.br/arquivos/extras/tiss/"
    "Padrao_TISS_Representacao_de_Conceitos_em_Saude_202609.zip"
)

SOURCE_TITLE = "Componente de Representação de Conceitos em Saúde — versão 202609, Tabela 38"

SOURCE_DATE = "2026-09"

SOURCE_LICENSE = "não informado"

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
}

ORIENTACOES = {
    "10": (
        "Confira a identificação e a elegibilidade na carteirinha e no cadastro; "
        "anexe os comprovantes ao recurso."
    ),
    "11": (
        "Confira número, valor e vínculo do protocolo com as guias; "
        "anexe o demonstrativo ao recurso."
    ),
    "12": (
        "Confira CNES, CPF/CNPJ e cadastro do prestador; anexe o comprovante cadastral ao recurso."
    ),
    "13": (
        "Confira identificação, preenchimento e reapresentação da guia; "
        "anexe a guia corrigida e os documentos solicitados."
    ),
    "14": (
        "Confira solicitante, senha, validade e procedimentos autorizados; "
        "anexe o comprovante de autorização ao recurso."
    ),
    "15": (
        "Confira o indicador de acidente e os campos relacionados na guia; "
        "anexe os documentos de suporte ao recurso."
    ),
    "16": (
        "Confira os registros do atendimento anterior e a regra administrativa citada; "
        "anexe os comprovantes no canal de recurso."
    ),
    "17": (
        "Confira quantidade, valor unitário, fator e totais informados; "
        "anexe memória de cálculo e documentos da cobrança."
    ),
    "18": (
        "Confira código, tabela, quantidade e documentos do procedimento; "
        "apresente a justificativa administrativa no recurso."
    ),
    "19": (
        "Confira datas, itens cobrados e registros que sustentam a permanência; "
        "anexe os documentos requeridos no recurso."
    ),
    "25": (
        "Confira códigos e quantidades dos itens odontológicos cobrados; "
        "anexe os registros correspondentes ao recurso."
    ),
    "26": (
        "Confira a identificação e participação profissional registradas; "
        "anexe os comprovantes solicitados pela operadora."
    ),
    "28": (
        "Confira a composição do pacote e os itens documentados; "
        "detalhe a cobrança e anexe os registros ao recurso."
    ),
    "29": (
        "Confira a decisão anterior e o prazo de reapresentação; "
        "encaminhe contestação fundamentada pelo canal de recurso."
    ),
    "30": (
        "Confira o status da análise e os documentos pendentes; "
        "acompanhe a liberação pelo canal indicado pela operadora."
    ),
    "31": (
        "Confira o código de origem e o cadastro de acesso do prestador; "
        "solicite ajuste cadastral à operadora."
    ),
    "32": (
        "Confira o registro de permanência associado ao item assistencial; "
        "anexe os documentos pertinentes ao recurso."
    ),
    "33": (
        "Confira os documentos e registros associados ao procedimento; "
        "encaminhe-os pelo canal de recurso da operadora."
    ),
    "50": (
        "Confira versão, estrutura e campos da mensagem TISS; "
        "corrija o XML e reenvie conforme o canal da operadora."
    ),
}


def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    kind = cell.attrib.get("t")
    value = cell.find("main:v", NS)
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", NS))
    raw = value.text if value is not None else ""
    if kind == "s" and raw:
        return shared[int(raw)]
    return raw


def _excel_date(value: str) -> str:
    if not value:
        return ""
    try:
        return (
            (datetime.datetime(1899, 12, 30) + datetime.timedelta(days=float(value)))
            .date()
            .isoformat()
        )
    except (ValueError, OverflowError):
        return value


def _xlsx_rows(raw: bytes) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(raw)) as workbook:
        shared = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            shared_root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            shared = [
                "".join(node.text or "" for node in item.findall(".//main:t", NS))
                for item in shared_root
            ]
        sheets = ET.fromstring(workbook.read("xl/workbook.xml")).find("main:sheets", NS)
        relationships = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        target = None
        for sheet in sheets if sheets is not None else []:
            if sheet.attrib.get("name") == "Tab 38":
                rel_id = sheet.attrib[f"{{{NS['rel']}}}id"]
                target = posixpath.normpath(posixpath.join("xl", targets[rel_id]))
                break
        if target is None:
            raise ValueError("A planilha oficial não contém a aba Tab 38")
        root = ET.fromstring(workbook.read(target))
        records = []
        for row in root.findall(".//main:sheetData/main:row", NS):
            values: dict[str, str] = {}
            for cell in row.findall("main:c", NS):
                column = re.sub(r"\d", "", cell.attrib.get("r", ""))
                values[column] = _cell_value(cell, shared)
            if values.get("A", "").strip() == "Código do Termo":
                continue
            code = values.get("A", "").strip()
            description = values.get("B", "")
            if code.isdigit() and description:
                records.append(
                    {
                        "codigo": code,
                        "descricao": description,
                        "grupo": code[:2],
                        "vigencia_inicio": _excel_date(values.get("C", "")),
                        "vigencia_fim": _excel_date(values.get("D", "")),
                    }
                )
        records.sort(key=lambda item: item["codigo"])
        if not records:
            raise ValueError("A planilha Tab 38 não contém termos")
        return records


def bake_glosas(archive: Path) -> dict[str, Any]:
    with zipfile.ZipFile(archive) as bundle:
        workbook_name = next(
            (
                name
                for name in bundle.namelist()
                if name.casefold().endswith(".xlsx") and "demais terminologias" in name.casefold()
            ),
            None,
        )
        if workbook_name is None:
            raise ValueError("Planilha TUSS - Demais terminologias ausente no ZIP ANS")
        records = _xlsx_rows(bundle.read(workbook_name))
    return {
        "version": 1,
        "source": {
            "titulo": SOURCE_TITLE,
            "url": SOURCE_URL,
            "data": SOURCE_DATE,
        },
        "license": SOURCE_LICENSE,
        "orientacoes": ORIENTACOES,
        "records": [
            {
                "codigo": row["codigo"],
                "descricao": row["descricao"],
                "grupo": row["grupo"],
                "orientacao": {
                    "texto": ORIENTACOES[row["grupo"]],
                    "fonte": "voa-tiss",
                },
                "fonte": {
                    "titulo": SOURCE_TITLE,
                    "url": SOURCE_URL,
                    "data": SOURCE_DATE,
                },
            }
            for row in records
        ],
    }


def write_outputs(dataset: dict[str, Any], out: Path, domain_path: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, dataset)
    domain = json.loads(domain_path.read_text(encoding="utf-8"))
    domain["tables"]["38"] = "Terminologia de mensagens (glosas, negativas e outras)"
    domain["table_info"] = [row for row in domain["table_info"] if str(row[0]) != "38"] + [
        ["38", domain["tables"]["38"], len(dataset["records"])]
    ]
    domain["table_info"].sort(key=lambda row: int(row[0]))
    domain["records"] = [row for row in domain["records"] if row["tabela"] != "38"] + [
        {
            "tabela": "38",
            "codigo": row["codigo"],
            "termo": row["descricao"],
            "descricao": row["descricao"],
            "vigencia_inicio": "",
            "vigencia_fim": "",
        }
        for row in dataset["records"]
    ]
    domain["records"].sort(key=lambda row: (int(row["tabela"]), row["codigo"]))
    domain["records_count"] = len(domain["records"])
    domain["sources"] = {
        "pda": domain["source"],
        "tabela38": dataset["source"],
    }
    write_json(domain_path, domain)
