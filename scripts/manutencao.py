"""Gere artefatos, prepare dados locais e verifique o repositório."""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from voa_tiss import examples, json_schema, validate
from voa_tiss.codes import CODES
from voa_tiss.server._ops import render_api_docs

if __package__:
    from ._manutencao_ans import (
        CADOP_URL,
        DOMAIN_OUT,
        GLOSA_DOMAIN,
        GLOSA_OUT,
        HEALTHPLANS_OUT,
        PDA_URL,
        TABELA38_URL,
        bake_domain,
        bake_glosas,
        bake_healthplans,
        write_outputs,
    )
    from ._manutencao_common import download, write_json
    from ._manutencao_descoberta import descoberta
    from ._manutencao_glosa import INDICADORES_OUT, baixar_painel, bake_painel, write_painel
    from ._manutencao_quality import normalise_notebooks
    from ._manutencao_quality import verificar as _verificar
    from ._manutencao_rede import REDE_MANIFEST, REDE_OUT, REDE_URL, bake_rede
    from ._manutencao_tuss import (
        DEFAULT_OUT,
        _finalise,
        _parse_table_arg,
        bake_table,
        bake_tuss_archive,
        write_dataset,
    )
else:
    from _manutencao_ans import (
        CADOP_URL,
        DOMAIN_OUT,
        GLOSA_DOMAIN,
        GLOSA_OUT,
        HEALTHPLANS_OUT,
        PDA_URL,
        TABELA38_URL,
        bake_domain,
        bake_glosas,
        bake_healthplans,
        write_outputs,
    )
    from _manutencao_common import download, write_json
    from _manutencao_descoberta import descoberta
    from _manutencao_glosa import INDICADORES_OUT, baixar_painel, bake_painel, write_painel
    from _manutencao_quality import normalise_notebooks
    from _manutencao_quality import verificar as _verificar
    from _manutencao_rede import REDE_MANIFEST, REDE_OUT, REDE_URL, bake_rede
    from _manutencao_tuss import (
        DEFAULT_OUT,
        _finalise,
        _parse_table_arg,
        bake_table,
        bake_tuss_archive,
        write_dataset,
    )

ROOT = Path(__file__).resolve().parents[1]
STYLE_TERMS = (
    r"charcot",
    r"voa-backend",
    r"(?<!tiss-)api\.voa\.health",
    r"\bPRD\b",
    r"\bUS\d+\b",
    r"\bD[0-9]{1,2}\b",
    r"(?<!SSE-)(?<!AWS::)\bS[1-7][bc]?\b(?![.:/])(?!\s+cp\b)",
    r"\bPR\b",
    r"\bissue\b",
    r"pull request",
    r"\bsess[aã]o(?:\s+S[1-7])?\b",
    r"legad",
    r"legacy",
    r"portad[oa] de",
    r"migrad",
    r"nesta vers[aã]o",
    r"uso futuro",
    r"por enquanto",
    r"\bTODO\b",
    r"FIXME",
    r"(?<!release/)(?<!/)\bv1\b(?!\.\d)",
    r"antes/agora",
    r"\bconvenio_batch_validator\b",
)
_STYLE_PATTERN = re.compile("|".join(STYLE_TERMS), re.IGNORECASE)
_SKIP_PREFIXES = ("tests/fixtures/",)


def _artifact_contents() -> dict[Path, bytes]:
    from voa_tiss.server import app as server_app

    artifacts = {
        ROOT / "schemas" / f"{name}.schema.json": (
            json.dumps(json_schema(name), ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
        )
        for name in ("finding", "report", "lote", "audit_context", "rules", "rejection_map")
    }
    lines = [
        "# Códigos estáveis de validação",
        "",
        "Os códigos abaixo fazem parte dos contratos públicos de validação e auditoria.",
        "",
        "| Código | Descrição |",
        "| --- | --- |",
    ]
    lines.extend(f"| `{code}` | {description} |" for code, description in sorted(CODES.items()))
    artifacts[ROOT / "docs" / "codigos.md"] = "\n".join(lines).encode("utf-8") + b"\n"
    golden = validate(examples.load("lote-com-erros")).to_json()
    artifacts[ROOT / "tests" / "golden" / "lote-com-erros.report.json"] = (golden + "\n").encode(
        "utf-8"
    )
    artifacts[ROOT / "docs" / "api.md"] = render_api_docs().encode("utf-8")
    artifacts[ROOT / "schemas" / "openapi.json"] = (
        json.dumps(server_app.openapi(), ensure_ascii=False, indent=2, sort_keys=True).encode(
            "utf-8"
        )
        + b"\n"
    )
    requirements = subprocess.run(
        [
            "uv",
            "export",
            "--frozen",
            "--extra",
            "server",
            "--no-hashes",
            "--no-emit-project",
            "--no-dev",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    artifacts[ROOT / "requirements.txt"] = requirements.encode("utf-8")
    return artifacts


def _write_artifacts(*, check: bool) -> bool:
    stale = False
    for path, expected in _artifact_contents().items():
        if check:
            if not path.is_file() or path.read_bytes() != expected:
                logging.error("Artefato desatualizado: %s", path.relative_to(ROOT))
                stale = True
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
    return not stale


def _bake_tables(*, tables: dict[str, Path], encoding: str, delimiter: str) -> dict[str, Any]:
    records = [
        record
        for table, path in tables.items()
        for record in bake_table(
            tabela=table, input_csv=path, encoding=encoding, delimiter=delimiter
        )
    ]
    return _finalise(records, table_ids=list(tables))


def _notebook_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(str(part) for part in value)
    return ""


def _tutorial_details(cells: list[dict[str, Any]]) -> tuple[str, str]:
    for cell in cells:
        if cell.get("cell_type") != "markdown":
            continue
        source = _notebook_text(cell.get("source"))
        heading = re.search(r"(?m)^#\s+(.+?)\s*$", source)
        if not heading:
            continue
        paragraph: list[str] = []
        for line in source[heading.end() :].splitlines():
            if not line.strip():
                if paragraph:
                    break
                continue
            paragraph.append(line.strip())
        description = " ".join(paragraph)
        if description:
            return heading.group(1), description
    raise ValueError("Notebook sem título H1 e parágrafo de descrição")


def _tutorial_source(source: str, notebook: Path, *, add_links: bool) -> str:
    source = re.sub(
        r"(?P<prefix>\]\()(?P<path>(?:\./)?\d{2}-[A-Za-z0-9-]+)\.ipynb"
        r"(?P<suffix>[?#][^)]*)?\)",
        lambda match: f"{match['prefix']}{match['path']}.md{match['suffix'] or ''})",
        source,
    )
    if not add_links:
        return source
    heading = re.search(r"(?m)^#\s+.+$", source)
    if not heading:
        return source
    github_url = "https://github.com/Voa-Health/tiss/blob/main/docs/tutoriais/" + notebook.name
    colab_url = (
        "https://colab.research.google.com/github/Voa-Health/tiss/blob/main/docs/tutoriais/"
        + notebook.name
    )
    links = f"[Abrir no GitHub]({github_url}) · [Abrir no Colab]({colab_url})"
    return f"{source[: heading.end()]}\n\n{links}\n\n{source[heading.end() :].lstrip()}"


def _tutorial_outputs(cell: dict[str, Any]) -> list[str]:
    outputs: list[str] = []
    for output in cell.get("outputs", []):
        if output.get("output_type") == "stream":
            text = _notebook_text(output.get("text"))
        elif output.get("output_type") in {"execute_result", "display_data"}:
            data = output.get("data")
            text = _notebook_text(data.get("text/plain")) if isinstance(data, dict) else ""
        else:
            continue
        if text.strip():
            outputs.append(text.rstrip("\n"))
    return outputs


def _render_tutorial(notebook_path: Path, notebook: dict[str, Any]) -> tuple[str, str, str]:
    cells = notebook.get("cells", [])
    title, description = _tutorial_details(cells)
    parts = [f"---\ndescription: {description}\n---"]
    links_added = False
    for cell in cells:
        cell_type = cell.get("cell_type")
        source = _notebook_text(cell.get("source")).strip("\n")
        if cell_type == "markdown":
            has_heading = bool(re.search(r"(?m)^#\s+.+$", source))
            parts.append(
                _tutorial_source(source, notebook_path, add_links=has_heading and not links_added)
            )
            links_added = links_added or has_heading
        elif cell_type == "code":
            parts.append(f"```python\n{source}\n```")
            parts.extend(f"```text\n{output}\n```" for output in _tutorial_outputs(cell))
    content = "\n\n".join(part for part in parts if part).rstrip() + "\n"
    return title, description, content


def gitbook_tutorials(destination: Path) -> int:
    tutorials: list[tuple[str, str, str, str]] = []
    for notebook_path in sorted((ROOT / "docs" / "tutoriais").glob("*.ipynb")):
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        if not isinstance(notebook, dict):
            raise ValueError(f"Notebook inválido: {notebook_path.name}")
        title, description, content = _render_tutorial(notebook_path, notebook)
        tutorials.append((notebook_path.stem, title, description, content))

    destination.mkdir(parents=True, exist_ok=True)
    intro = "Exemplos práticos com dados sintéticos para integrar o voa-tiss."
    index = ["# Tutoriais", "", intro, ""]
    for slug, title, description, content in tutorials:
        index.append(f"- [{title}]({slug}.md): {description}")
        (destination / f"{slug}.md").write_text(content, encoding="utf-8")
    (destination / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return 0


def verificar() -> int:
    return _verificar(_STYLE_PATTERN, _SKIP_PREFIXES, lambda: _write_artifacts(check=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    download_command = commands.add_parser("baixar", help="baixar fontes públicas da ANS")
    download_command.add_argument("--out", type=Path, default=Path("/tmp/voa-tiss-ans"))
    artifacts = commands.add_parser("artefatos", help="gerar esquemas, códigos e notebooks")
    artifacts.add_argument("--check", action="store_true")
    tuss = commands.add_parser("tuss", help="preparar dados TUSS")
    tuss.add_argument("--pda-zip", type=Path)
    tuss.add_argument("--table", dest="tables", action="append", default=[], type=_parse_table_arg)
    tuss.add_argument("--out", type=Path, default=DEFAULT_OUT)
    tuss.add_argument("--encoding", default="utf-8")
    tuss.add_argument("--delimiter", default=";")
    domain = commands.add_parser("dominio", help="preparar domínios e operadoras")
    domain.add_argument("--pda-zip", type=Path, required=True)
    domain.add_argument("--cadop-csv", type=Path, required=True)
    domain.add_argument("--domain-out", type=Path, default=DOMAIN_OUT)
    domain.add_argument("--healthplans-out", type=Path, default=HEALTHPLANS_OUT)
    table38 = commands.add_parser("tabela38", help="preparar glosas e tabela 38")
    table38.add_argument("--archive", type=Path, required=True)
    table38.add_argument("--out", type=Path, default=GLOSA_OUT)
    table38.add_argument("--domain-out", type=Path, default=GLOSA_DOMAIN)
    painel = commands.add_parser("ans-glosa", help="preparar o painel de glosas da ANS")
    painel.add_argument("--origem", type=Path, help="pasta com os CSVs já baixados")
    painel.add_argument("--out", type=Path, default=INDICADORES_OUT)
    xsd = commands.add_parser("xsd402", help="instalar os esquemas TISS 4.02.00")
    xsd.add_argument("--source", type=Path, required=True)
    xsd.add_argument("--out", type=Path, default=ROOT / "src/voa_tiss/_data/schemas/4.02.00")
    commands.add_parser("verificar", help="verificar padrões, exemplos e artefatos")
    gitbook = commands.add_parser("gitbook", help="gerar páginas GitBook dos tutoriais")
    gitbook.add_argument("destination", type=Path)
    rede = commands.add_parser("ans-rede", help="preparar o SQLite da rede hospitalar")
    rede.add_argument("--zip", type=Path, required=True)
    rede.add_argument("--out", type=Path, default=REDE_OUT)
    rede.add_argument("--manifesto", type=Path, default=REDE_MANIFEST)
    avaliacao = commands.add_parser("descoberta", help="medir descoberta do voa-tiss em modelos")
    avaliacao.add_argument("--limite-usd", type=float, default=10.0)
    avaliacao.add_argument("--teto-chamada-usd", type=float, default=0.25)
    avaliacao.add_argument("--brutos", type=Path, help="pasta fora do repo para respostas")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.command == "baixar":
        for name, url in {
            "pda-049-tuss.zip": PDA_URL,
            "Relatorio_cadop.csv": CADOP_URL,
            "tabela38.zip": TABELA38_URL,
            "produtos_e_prestadores_hospitalares.zip": REDE_URL,
        }.items():
            path = args.out / name
            logging.info("%s sha256=%s", path, download(url, path))
        return 0
    if args.command == "artefatos":
        checks = (
            _write_artifacts(check=args.check),
            normalise_notebooks(check=args.check),
        )
        return 0 if all(checks) else 1
    if args.command == "verificar":
        return verificar()
    if args.command == "gitbook":
        return gitbook_tutorials(args.destination)
    if args.command == "descoberta":
        return descoberta(args.limite_usd, args.brutos, teto_chamada_usd=args.teto_chamada_usd)
    if args.command == "dominio":
        write_json(args.domain_out, bake_domain(args.pda_zip))
        write_json(args.healthplans_out, bake_healthplans(args.cadop_csv))
        return 0
    if args.command == "tabela38":
        write_outputs(bake_glosas(args.archive), args.out, args.domain_out)
        return 0
    if args.command == "ans-rede":
        logging.info(
            "%s",
            json.dumps(bake_rede(args.zip, args.out, args.manifesto), ensure_ascii=False),
        )
        return 0
    if args.command == "ans-glosa":
        origem = args.origem or Path("/tmp/voa-tiss-ans/painel_de_glosas")
        if not args.origem:
            baixar_painel(origem)
        write_painel(args.out, bake_painel(origem))
        return 0
    if args.command == "xsd402":
        args.out.mkdir(parents=True, exist_ok=True)
        for path in args.source.iterdir():
            if path.is_file():
                shutil.copy2(path, args.out / path.name)
        return 0
    if args.pda_zip:
        write_dataset(bake_tuss_archive(args.pda_zip), args.out)
        return 0
    if not args.tables:
        parser.error("informe --pda-zip ou --table")
    tables: dict[str, Path] = {}
    for table, path in args.tables:
        if table in tables:
            logging.error("Tabela repetida: %s", table)
            return 2
        if not path.is_file():
            logging.error("Arquivo não encontrado para tabela %s: %s", table, path)
            return 2
        tables[table] = path
    dataset = _bake_tables(tables=tables, encoding=args.encoding, delimiter=args.delimiter)
    write_dataset(dataset, args.out)
    logging.info("Dados gravados em %s (%d registros)", args.out, len(dataset["records"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
