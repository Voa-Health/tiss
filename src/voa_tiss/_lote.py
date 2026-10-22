"""Tipos e tabelas para lotes TISS 4.03.00."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class LoteError(ValueError):
    """A entrada não pode ser representada como lote TISS 4.03.00."""


class Transacao(TypedDict):
    sequencial_transacao: str
    data_registro_transacao: str
    hora_registro_transacao: str


class Prestador(TypedDict):
    cnpj: str


class Operadora(TypedDict):
    registro_ans: str


class Guia(TypedDict, total=False):
    tipo: Literal["consulta", "sp_sadt"]
    cabecalho_guia: dict[str, Any]
    cabecalho_consulta: dict[str, Any]
    dados_beneficiario: dict[str, Any]
    dados_solicitante: dict[str, Any]
    dados_solicitacao: dict[str, Any]
    contratado_executante: dict[str, Any]
    profissional_executante: dict[str, Any]
    indicacao_acidente: str
    dados_atendimento: dict[str, Any]
    procedimentos_executados: list[dict[str, Any]]
    valor_total: dict[str, Any]
    numero_guia_operadora: str
    ausencia_cod_validacao: str
    cod_validacao: str
    observacao: str


class Lote(TypedDict):
    versao: str
    transacao: Transacao
    prestador: Prestador
    operadora: Operadora
    numero_lote: str
    guias: list[Guia]


_TAGS = {
    "cbos": "CBOS",
    "cbo": "CBO",
    "uf": "UF",
    "cnes": "CNES",
    "cnpj": "CNPJ",
    "cpf": "CPF",
    "ans": "ANS",
    "padrao": "Padrao",
    "registro_ans": "registroANS",
    "atendimento_rn": "atendimentoRN",
}
_MONEY = {
    "valor_procedimento",
    "valor_unitario",
    "valor_total",
    "valor_total_geral",
    "valor_procedimentos",
    "valor_diarias",
    "valor_taxas",
    "valor_materiais",
    "valor_opme",
    "valor_medicamentos",
    "valor_gases_medicinais",
}
_ORDERS: dict[str, tuple[str, ...]] = {
    "transacao": (
        "sequencial_transacao",
        "data_registro_transacao",
        "hora_registro_transacao",
    ),
    "prestador": ("cnpj", "cpf", "codigo_prestador_na_operadora"),
    "guia": (
        "cabecalho_consulta",
        "cabecalho_guia",
        "numero_guia_operadora",
        "ausencia_cod_validacao",
        "cod_validacao",
        "dados_autorizacao",
        "dados_beneficiario",
        "dados_solicitante",
        "dados_solicitacao",
        "dados_executante",
        "contratado_executante",
        "profissional_executante",
        "indicacao_acidente",
        "dados_atendimento",
        "procedimentos_executados",
        "outras_despesas",
        "observacao",
        "valor_total",
    ),
    "cabecalho_guia": (
        "registro_ans",
        "numero_guia_prestador",
        "numero_guia_operadora",
        "guia_principal",
    ),
    "dados_beneficiario": ("numero_carteira", "atendimento_rn", "nome_beneficiario"),
    "dados_executante": ("contratado_executante", "cnes", "profissional_executante"),
    "contratado_executante": (
        "codigo_prestador_na_operadora",
        "cpf_contratado",
        "cnpj_contratado",
        "nome_contratado",
        "cnes",
    ),
    "dados_atendimento": (
        "tipo_atendimento",
        "indicacao_acidente",
        "regime_atendimento",
        "cobertura_especial",
        "saude_ocupacional",
        "data_atendimento",
    ),
    "dados_atendimento_consulta": (
        "cobertura_especial",
        "regime_atendimento",
        "saude_ocupacional",
        "data_atendimento",
        "tipo_consulta",
        "procedimento",
    ),
    "procedimento": ("codigo_tabela", "codigo_procedimento", "descricao_procedimento"),
    "profissional_solicitante": (
        "nome_profissional",
        "conselho_profissional",
        "numero_conselho_profissional",
        "uf",
        "cbos",
    ),
    "profissional_executante": (
        "nome_profissional",
        "conselho_profissional",
        "numero_conselho_profissional",
        "uf",
        "cbos",
    ),
    "procedimento_executado": (
        "sequencial_item",
        "data_execucao",
        "hora_inicial",
        "hora_final",
        "procedimento",
        "quantidade_executada",
        "via_acesso",
        "tecnica_utilizada",
        "reducao_acrescimo",
        "valor_unitario",
        "valor_total",
        "equipe_sadt",
    ),
    "valor_total": (
        "valor_procedimentos",
        "valor_diarias",
        "valor_taxas",
        "valor_materiais",
        "valor_opme",
        "valor_medicamentos",
        "valor_gases_medicinais",
        "valor_total_geral",
    ),
}
_LIST_TAGS = {
    "equipe_sadt": "equipeSadt",
    "procedimentos_executados": "procedimentoExecutado",
}
