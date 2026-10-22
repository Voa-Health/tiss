# Contribuindo

## Ambiente

Instale [uv](https://docs.astral.sh/uv/) e prepare o projeto:

```sh
uv sync --all-extras --group dev
uvx pre-commit install
```

## Padrões

- Escreva textos curtos.
- Comente apenas para explicar uma intenção não óbvia.
- Descreva o que o código é, sem histórico, origem, decisões, processo ou nomes internos.
- Siga DRY: um conceito, uma declaração.
- Prefira poucos testes parametrizados pela API pública.
- Use apenas dados sintéticos nos testes.
- Escreva tutoriais em notebooks.
- Consulte `LIMITES` em `scripts/manutencao.py` para as guardas automáticas.
- Rode `uv run python scripts/manutencao.py verificar` antes de enviar.
- O Gitleaks bloqueia segredos na CI e no pre-commit.

## Como contribuir

Antes de enviar, execute:

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/manutencao.py artefatos --check
uv run python scripts/manutencao.py verificar
uv run pytest --nbmake docs/tutoriais
```

Para o site em `web/`, execute:

```sh
cd web && pnpm install && pnpm lint && pnpm typecheck && pnpm build
```

O site permite indexação quando `VERCEL_ENV=production`. Em previews e no
ambiente local, o `robots.txt` bloqueia rastreamento e as páginas usam `noindex`.
`NEXT_PUBLIC_INDEXAR=0` desativa a indexação também em produção. Essa configuração
é aplicada no build. As páginas de acesso, chaves e organização usam `noindex`
e não entram no sitemap.
