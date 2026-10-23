"""Testes da rede hospitalar com dados sintéticos."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from scripts._manutencao_rede import bake_rede
from voa_tiss import rede
from voa_tiss.operadoras import lookup
from voa_tiss.server._http import create_app
from voa_tiss.server._ops import OPS, token_estimate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def rede_sintetica(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, Any], Path]:
    """Gere uma base temporária a partir de CSVs sintéticos."""
    diretorio = tmp_path_factory.mktemp("rede")
    arquivo_zip = diretorio / "fonte.zip"
    with zipfile.ZipFile(arquivo_zip, "w") as pacote:
        for uf in ("SP", "RJ"):
            pacote.write(ROOT / "tests" / "fixtures" / "rede" / f"{uf}.csv", f"{uf}.csv")
    saida = diretorio / "saida"
    manifesto = diretorio / "manifesto.json"
    resultado = bake_rede(arquivo_zip, saida, manifesto, workers=1)
    return saida / "rede-hospitalar.sqlite", resultado, arquivo_zip


def test_rede_consultas_e_validacoes(
    rede_sintetica: tuple[Path, dict[str, Any], Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Consulta vínculos, atributos agregados e metadados."""
    banco, _, _ = rede_sintetica
    monkeypatch.setenv("VOA_TISS_REDE", str(banco))
    rede._conectar.cache_clear()

    por_cnpj = rede.operadoras_do_estabelecimento(cnpj="12.345.678/0001-95")
    assert por_cnpj == [
        {
            "registro_ans": "000515",
            "nome": lookup("000515")["razao_social"],
            "cnes": "0123456",
            "nome_estabelecimento": "Hospital Sintético SP",
            "tipo_contrato": ["Próprio", "Referenciado"],
            "disponibilidade": ["12h", "24h"],
            "tipo_prestador": ["Hospital", "Pronto atendimento"],
            "urgencia_emergencia": True,
            "dt_vinculo_inicio": "2023-02-01",
            "planos": 2,
        }
    ]
    por_cnes = rede.operadoras_do_estabelecimento(cnes="7654321")
    assert por_cnes[0]["nome_estabelecimento"] == "Hospital Sintético RJ"
    assert rede.operadoras_do_estabelecimento(cnes="0000001") == []

    estabelecimentos = rede.estabelecimentos_da_operadora("000515")
    assert [(item["uf"], item["cnes"]) for item in estabelecimentos] == [
        ("RJ", "7654321"),
        ("SP", "0123456"),
    ]
    assert "id" not in estabelecimentos[0]
    assert len(rede.estabelecimentos_da_operadora("000515", uf="rj")) == 1
    assert rede.resumo_da_operadora("000515") == {
        "registro_ans": "000515",
        "estabelecimentos": 2,
        "por_uf": {"RJ": 1, "SP": 1},
    }
    assert rede.resumo_da_operadora("999999")["estabelecimentos"] == 0
    assert rede.atualizado_em() == "2025-01-31"
    assert "Produtos e Prestadores Hospitalares" in rede.fonte()

    with pytest.raises(ValueError):
        rede.operadoras_do_estabelecimento()
    with pytest.raises(ValueError):
        rede.operadoras_do_estabelecimento(cnpj="12345678000100")
    with pytest.raises(ValueError):
        rede.operadoras_do_estabelecimento(cnes="0000000")
    with pytest.raises(ValueError):
        rede.estabelecimentos_da_operadora("000515", uf="RJX")
    with pytest.raises(ValueError):
        rede.resumo_da_operadora("abc")


def test_rede_bake_deterministico(
    rede_sintetica: tuple[Path, dict[str, Any], Path], tmp_path: Path
) -> None:
    """Gera os mesmos bytes para uma mesma origem."""
    banco, _, arquivo_zip = rede_sintetica
    saida = tmp_path / "segunda"
    bake_rede(arquivo_zip, saida, tmp_path / "manifesto.json", workers=1)
    assert (saida / banco.name).read_bytes() == banco.read_bytes()


def test_rede_download_cache_offline_e_hash_invalido(
    rede_sintetica: tuple[Path, dict[str, Any], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Baixa somente bytes verificados e reutiliza o cache offline."""
    banco, manifesto, _ = rede_sintetica
    comprimido = banco.with_name(f"{banco.name}.gz")
    manifesto_path = tmp_path / "manifesto.json"
    dados = {**manifesto, "url": comprimido.as_uri()}
    manifesto_path.write_text(json.dumps(dados), encoding="utf-8")
    monkeypatch.setattr(rede, "_MANIFEST_PATH", manifesto_path)
    monkeypatch.delenv("VOA_TISS_REDE", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    rede._conectar.cache_clear()

    assert rede.atualizado_em() == "2025-01-31"
    dados["url"] = (tmp_path / "ausente.gz").as_uri()
    manifesto_path.write_text(json.dumps(dados), encoding="utf-8")
    assert rede.fonte().startswith("ANS, Produtos e Prestadores Hospitalares")

    dados["url"] = comprimido.as_uri()
    dados["sha256"] = "0" * 64
    manifesto_path.write_text(json.dumps(dados), encoding="utf-8")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache-invalido"))
    with pytest.raises(rede.RedeIndisponivel, match="não corresponde"):
        rede._caminho_banco()


def test_rede_rotas_http(
    rede_sintetica: tuple[Path, dict[str, Any], Path],
    monkeypatch: pytest.MonkeyPatch,
    tiss_service: Any,
) -> None:
    """Expõe as consultas HTTP com validação de entrada."""
    banco, _, _ = rede_sintetica
    monkeypatch.setenv("VOA_TISS_REDE", str(banco))
    rede._conectar.cache_clear()
    app = create_app()
    with TestClient(app, headers={"Authorization": "Bearer sk_tiss_verified"}) as cliente:
        resposta = cliente.get("/v1/rede", params={"cnes": "0123456", "limite": 1})
        assert resposta.status_code == 200
        assert token_estimate(resposta.json()) <= next(
            op.max_tokens for op in OPS if op.name == "rede"
        )
        assert resposta.json()["total"] == 1
        assert resposta.json()["operadoras"][0]["registro_ans"] == "000515"

        resposta = cliente.get("/v1/operadoras/000515/rede", params={"uf": "rj", "limite": 1})
        assert resposta.status_code == 200
        assert token_estimate(resposta.json()) <= next(
            op.max_tokens for op in OPS if op.name == "operadora_rede"
        )
        assert resposta.json()["registro_ans"] == "000515"
        assert resposta.json()["total"] == 2
        assert len(resposta.json()["estabelecimentos"]) == 1

        assert cliente.get("/v1/rede", params={"cnpj": "00000000000000"}).status_code == 422
        assert cliente.get("/v1/operadoras/000515/rede", params={"uf": "RJJ"}).status_code == 422
        parametros = cliente.get("/openapi.json").json()["paths"]["/v1/operadoras/{registro}/rede"][
            "get"
        ]["parameters"]
        assert any(
            parametro["name"] == "registro" and parametro["in"] == "path"
            for parametro in parametros
        )

        monkeypatch.setenv("VOA_TISS_REDE", str(banco / "ausente.sqlite"))
        indisponivel = cliente.get("/v1/rede", params={"cnes": "0123456"})
        assert indisponivel.status_code == 503
        assert indisponivel.headers["retry-after"] == "1"
