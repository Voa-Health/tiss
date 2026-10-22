from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

from bench._agente import (
    executar_tarefa,
    ferramenta_python,
    listar_ferramentas_mcp,
    parametros_modelo,
)
from bench._tarefas import TASK_DIR, escrever

_SUMMARY_FIELDS = (
    "id",
    "categoria",
    "perspectiva",
    "modelo",
    "modo",
    "data",
    "parametros",
    "passos",
    "tokens_entrada",
    "tokens_saida",
    "custo_usd",
    "ok",
    "motivo",
    "erro",
    "finish_reason",
)


def _tasks() -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8")) for path in sorted(TASK_DIR.glob("*.json"))
    ]


def _run(args: argparse.Namespace) -> None:
    selected = _tasks()
    if args.tarefas:
        requested = {item.strip() for item in args.tarefas.split(",") if item.strip()}
        selected = [task for task in selected if task["id"] in requested]
        missing = requested - {task["id"] for task in selected}
        if missing:
            raise SystemExit("Tarefas desconhecidas: " + ", ".join(sorted(missing)))
    if not selected:
        raise SystemExit("Nenhuma tarefa encontrada; execute `gerar` primeiro.")
    selected.sort(key=lambda task: task["id"])
    ferramenta_python("pass")
    model_parameters = parametros_modelo(args.modelo)
    if args.modo == "com_mcp":
        listar_ferramentas_mcp()
    run_date = date.today().isoformat()
    slug = args.modelo.replace("/", "__")
    output_dir = Path(args.saida) / run_date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{slug}__{args.modo}.jsonl"
    with ThreadPoolExecutor(max_workers=args.paralelo) as executor:
        results = list(
            executor.map(
                lambda task: executar_tarefa(
                    task,
                    args.modelo,
                    args.modo,
                    run_date,
                    model_parameters,
                ),
                selected,
            )
        )
    with output_path.open("w", encoding="utf-8") as output:
        for result in sorted(results, key=lambda item: item["id"]):
            output.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    print(output_path)


def _summarize(transcription_dir: Path, run_date: str | None) -> None:
    if run_date is None:
        run_date = date.today().isoformat()
    try:
        parsed_date = date.fromisoformat(run_date)
    except ValueError as error:
        raise SystemExit("--data deve estar no formato AAAA-MM-DD") from error
    if parsed_date.isoformat() != run_date:
        raise SystemExit("--data deve estar no formato AAAA-MM-DD")

    source_dir = transcription_dir / run_date
    sources = sorted(source_dir.glob("*.jsonl"))
    if not sources:
        raise SystemExit(f"Nenhuma transcrição encontrada em {source_dir}.")

    rows = []
    for source in sources:
        with source.open(encoding="utf-8") as transcript:
            for line_number, line in enumerate(transcript, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as error:
                    raise SystemExit(f"JSON inválido em {source}:{line_number}.") from error
                if not isinstance(row, dict):
                    raise SystemExit(f"Registro inválido em {source}:{line_number}.")
                summary = {field: row.get(field) for field in _SUMMARY_FIELDS}
                if isinstance(summary["erro"], str):
                    summary["erro"] = summary["erro"][:300]
                rows.append(summary)
    rows.sort(
        key=lambda row: (
            str(row["modelo"] or ""),
            str(row["modo"] or ""),
            str(row["id"] or ""),
        )
    )

    output_path = Path("bench/resultados") / run_date / "resumo.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(output_path)


def _table(directory: Path) -> None:
    runs: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for path in sorted(directory.rglob("resumo.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = (
                row["modelo"],
                row["modelo"].replace("/", "__"),
                row["data"],
                row["modo"],
            )
            runs.setdefault(key, []).append(row)
    if not runs:
        print("Nenhum resultado encontrado.")
        return
    categories = sorted({row["categoria"] for rows in runs.values() for row in rows})
    perspectives = sorted({row["perspectiva"] for rows in runs.values() for row in rows})
    headers = ["Modelo", "Slug", "Data", "Modo", "Erros"]
    headers.extend(f"{category} (%)" for category in categories)
    headers.extend(f"{perspective} (%)" for perspective in perspectives)
    headers.extend(["Total (%)", "Custo (US$)"])
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for (model, slug, run_date, mode), rows in sorted(runs.items()):
        cells = [
            model,
            slug,
            run_date,
            mode,
            str(sum(bool(row.get("erro")) for row in rows)),
        ]
        for category in categories:
            subset = [row for row in rows if row["categoria"] == category]
            cells.append(_percentage(subset))
        for perspective in perspectives:
            subset = [row for row in rows if row["perspectiva"] == perspective]
            cells.append(_percentage(subset))
        cells.append(_percentage(rows))
        cells.append(f"{sum(float(row.get('custo_usd', 0)) for row in rows):.6f}")
        print("| " + " | ".join(cells) + " |")


def _percentage(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "—"
    return f"{100 * sum(bool(row['ok']) for row in rows) / len(rows):.1f}"


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m bench")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("gerar", help="gere os arquivos determinísticos das tarefas")
    run = commands.add_parser("run", help="execute tarefas em um modelo OpenRouter")
    run.add_argument("--modelo", required=True)
    run.add_argument("--modo", choices=("sem_mcp", "com_mcp"), required=True)
    run.add_argument("--tarefas", help="IDs separados por vírgula")
    run.add_argument("--saida", default=".bench/transcricoes")
    run.add_argument("--paralelo", type=int, default=4)
    summarize = commands.add_parser(
        "resumir", help="gere um resumo compacto das transcrições de uma data"
    )
    summarize.add_argument("--transcricoes", type=Path, default=Path(".bench/transcricoes"))
    summarize.add_argument("--data")
    table = commands.add_parser("tabela", help="imprima tabelas Markdown a partir dos resumos")
    table.add_argument("diretorio", type=Path)
    args = parser.parse_args()
    if args.command == "gerar":
        tasks = escrever()
        print(f"{len(tasks)} tarefas gravadas em {TASK_DIR}")
    elif args.command == "run":
        if args.paralelo < 1:
            raise SystemExit("--paralelo deve ser maior que zero")
        _run(args)
    elif args.command == "resumir":
        _summarize(args.transcricoes, args.data)
    else:
        _table(args.diretorio)


if __name__ == "__main__":
    main()
