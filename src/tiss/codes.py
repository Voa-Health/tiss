"""Códigos estáveis retornados pelas APIs de validação e auditoria."""

from typing import Any


def _spec(
    message: str,
    *,
    severity: str = "error",
    glosa: str | None = None,
    fix_kind: str | None = None,
    needs: str | None = None,
) -> dict[str, Any]:
    return {
        "message": message,
        "severity": severity,
        "glosa": glosa,
        "fix_kind": fix_kind,
        "needs": needs,
    }


CODE_CATALOG = {
    "xml.malformado": _spec("XML malformado", glosa="5002"),
    "xml.doctype": _spec("DOCTYPE não permitido"),
    "xml.encoding": _spec("Codificação XML inválida"),
    "versao.nao_detectada": _spec("Versão TISS não detectada"),
    "versao.nao_suportada": _spec("Versão TISS não suportada", glosa="5028"),
    "versao.divergente": _spec(
        "Versão informada difere do XML", glosa="5028", fix_kind="json_patch"
    ),
    "xsd.elemento_inesperado": _spec("Elemento inesperado"),
    "xsd.elemento_ausente": _spec("Elemento obrigatório ausente"),
    "xsd.padrao": _spec("Valor fora do padrão"),
    "xsd.enumeracao": _spec("Valor fora da enumeração"),
    "xsd.tamanho": _spec("Tamanho inválido"),
    "xsd.tipo": _spec("Tipo inválido"),
    "xsd.atributo": _spec("Atributo inválido"),
    "xsd.outro": _spec("Erro de validação XSD"),
    "lote.guia_duplicada": _spec("Número de guia duplicado"),
    "lote.valor_total_geral": _spec("Total geral divergente", fix_kind="json_patch"),
    "lote.estrutura": _spec("Estrutura do lote inválida"),
    "lote.caractere_invalido": _spec("Caractere incompatível com ISO-8859-1"),
    "lote.hash_divergente": _spec("Hash do epílogo divergente", glosa="5014"),
    "guia.sequencial": _spec("Sequencial de itens inválido", glosa="3167", fix_kind="json_patch"),
    "guia.carteirinha_ausente": _spec("Carteirinha ausente", glosa="1001", needs="pointer"),
    "guia.executante_ausente": _spec("Dados do executante ausentes", glosa="1311", needs="pointer"),
    "item.valor_zerado": _spec("Valor do item ausente ou zerado", needs="pointer"),
    "item.valor_divergente": _spec("Valor do item divergente", fix_kind="json_patch"),
    "audit.procedimento_ausente": _spec("Procedimento ausente", needs="pointer"),
    "audit.procedimento_fora_da_tabela": _spec(
        "Procedimento fora da tabela da operadora", glosa="1801", needs="pointer"
    ),
    "audit.carteirinha_ausente": _spec("Carteirinha ausente", glosa="1001", needs="pointer"),
    "audit.carteirinha_inativa": _spec("Carteirinha inativa", needs="pointer"),
    "audit.carteirinha_vencida": _spec("Carteirinha vencida", glosa="1017", needs="pointer"),
    "audit.autorizacao_ausente": _spec("Autorização ausente", glosa="1425", needs="pointer"),
    "audit.autorizacao_vencida": _spec("Autorização vencida", glosa="1414", needs="pointer"),
    "audit.tabela_fora_de_vigencia": _spec("Tabela fora de vigência", needs="pointer"),
    "audit.operadora_divergente": _spec("Operadora divergente", glosa="5027", needs="pointer"),
    "audit.valor_nao_positivo": _spec("Valor não positivo", needs="pointer"),
    "audit.tabela_sem_procedimentos": _spec("Tabela sem procedimentos", needs="pointer"),
    "audit.data_ausente": _spec(
        "Data do atendimento ausente", severity="warning", glosa="3226", needs="pointer"
    ),
    "lote.vazio": _spec("Lote sem guias", needs="pointer"),
    "lote.acima_do_teto": _spec("Lote acima do limite de guias", needs="pointer"),
    "tuss.inexistente": _spec("Código TUSS inexistente", glosa="1801", needs="pointer"),
    "tuss.fora_de_vigencia": _spec("Código TUSS fora de vigência", glosa="1801", needs="pointer"),
    "regra.obrigatorio": _spec("Campo obrigatório ausente", needs="pointer"),
    "regra.padrao": _spec("Valor fora do padrão da operadora", needs="pointer"),
    "regra.valores": _spec("Valor não permitido pela operadora", needs="pointer"),
    "regra.max_itens": _spec("Limite de itens da operadora excedido", needs="pointer"),
    "regra.combinacao_proibida": _spec("Combinação proibida pela operadora", needs="pointer"),
    "regra.exige_autorizacao": _spec(
        "Procedimento exige autorização prévia", glosa="1818", needs="pointer"
    ),
    "autorizacao.sem_regra": _spec(
        "Sem regra da operadora para decidir a autorização.", severity="warning"
    ),
    "autorizacao.dado_ausente": _spec(
        "Dado necessário para analisar a autorização ausente.",
        severity="warning",
        needs="pointer",
    ),
    "autorizacao.exige_auditoria": _spec(
        "Procedimento exige autorização prévia.", severity="warning", needs="pointer"
    ),
    "autorizacao.carteirinha": _spec(
        "Carteirinha inativa ou vencida.", severity="warning", needs="pointer"
    ),
}

CODES: dict[str, str] = {code: values["message"] for code, values in CODE_CATALOG.items()}
