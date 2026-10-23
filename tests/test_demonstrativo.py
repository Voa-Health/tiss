"""Testes do parser de demonstrativos."""

from __future__ import annotations

import pytest
from conftest import ROOT, UserGuide, parse_return, return_guide

from tiss import (
    Decisao,
    Decision,
    RetornoError,
    examples,
    parse_demonstrativo,
    plan_reconciliation,
    validate,
)

FULL_AMOUNT_CENTS = 10_000
PARTIAL_GLOSS_CENTS = 1_000


def test_demonstrativo_parse_and_return_decisions():
    """Interprete decisões e o formato oficial."""
    decisions = parse_demonstrativo(examples.load("demonstrativo"))
    assert decisions[0].guia_ref == "EXEMPLO-001"
    assert decisions[0].to_dict()["guia_ref"] == "EXEMPLO-001"
    paid, gloss, partial = [
        parse_demonstrativo(parse_return(return_guide(*values)))[0]
        for values in (
            ("P1", "O1", "100.00", "0.00", ""),
            ("P2", "O2", "0.00", "100.00", "1401"),
            ("P3", "O3", "90.00", "10.00", "1401"),
        )
    ]
    official_xml = (ROOT / "tests/fixtures/demonstrativo-oficial.xml").read_bytes()
    assert validate(official_xml).valid
    [official] = parse_demonstrativo(official_xml)
    assert paid.decision == Decision.PAGO and paid.valor_liberado_cents == FULL_AMOUNT_CENTS
    assert gloss.decision == Decision.GLOSADO and gloss.valor_glosa_cents == FULL_AMOUNT_CENTS
    assert (
        partial.decision == Decision.GLOSA_PARCIAL
        and partial.valor_glosa_cents == PARTIAL_GLOSS_CENTS
    )
    assert official == Decisao(
        "0001", Decision.GLOSA_PARCIAL, "3209", "RET-0001", "10101012", 4000, 6000
    )
    with pytest.raises(ValueError):
        parse_demonstrativo("<not-closed>")


def test_reconciliation_is_read_only_and_handles_ambiguity():
    """Reconcilie decisões sem alterar as guias."""
    [decision] = parse_demonstrativo(parse_return(return_guide("P1", "O1", "100.00", "0.00")))
    guide = UserGuide("id1", "P1", "O1")
    result = plan_reconciliation([decision], [guide])
    assert result.propostas[0].guia is guide
    assert result.propostas[0].acao == "pagar"
    guide.status = "pago"
    assert not plan_reconciliation([decision], [guide]).propostas

    duplicate = [
        {"id": "a", "numero_guia_prestador": "P1"},
        {"id": "b", "numero_guia_prestador": "P1"},
    ]
    assert plan_reconciliation([decision], duplicate).ambiguas == [decision]
    mixed = [decision, decision._replace(decision=Decision.GLOSADO)]
    assert plan_reconciliation(mixed, [{"id": "x", "numero_guia_prestador": "P1"}]).ambiguas
    with pytest.raises(RetornoError, match="identificador"):
        plan_reconciliation([decision], [{"numero_guia_prestador": "P1"}])
