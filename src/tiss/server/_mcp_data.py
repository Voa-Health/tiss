from __future__ import annotations

RESOURCE_DEFINITIONS = (
    {
        "name": "codigos",
        "uri": "tiss://codigos",
        "description": "Códigos estáveis de validação.",
        "mime_type": "application/json",
    },
    {
        "name": "catalogo-sadt",
        "uri": "tiss://sadt/catalogo",
        "description": "Campos do catálogo SP/SADT.",
        "mime_type": "application/json",
    },
    {
        "name": "readme",
        "uri": "tiss://docs/readme",
        "description": "Documentação principal.",
        "mime_type": "text/markdown",
    },
    {
        "name": "api",
        "uri": "tiss://docs/api",
        "description": "Operações HTTP e tools MCP.",
        "mime_type": "text/markdown",
    },
    {
        "name": "schema-lote",
        "uri": "tiss://schemas/lote",
        "description": "Schema JSON estrutural para lotes TISS.",
        "mime_type": "application/json",
    },
    {
        "name": "dominio-tabelas",
        "uri": "tiss://dominio/tabelas",
        "description": "Tabelas de domínio TISS e suas fontes.",
        "mime_type": "application/json",
    },
    {
        "name": "operadoras",
        "uri": "tiss://operadoras",
        "description": "Origem e quantidade de operadoras locais.",
        "mime_type": "application/json",
    },
    {
        "name": "regras-schema",
        "uri": "tiss://regras/schema",
        "description": "Esquema dos pacotes de regras por operadora.",
        "mime_type": "application/json",
    },
)

RESOURCE_TEMPLATE_DEFINITIONS = (
    {
        "name": "tuss-paginado",
        "uri_template": "tiss://tuss/{tabela}/{pagina}",
        "description": "Página local do catálogo TUSS.",
        "mime_type": "application/json",
    },
    {
        "name": "dominio-tabela",
        "uri_template": "tiss://dominio/{tabela}",
        "description": "Registros locais de uma tabela de domínio TISS.",
        "mime_type": "application/json",
    },
    {
        "name": "operadora-perfil",
        "uri_template": "tiss://operadoras/{registro_ans}",
        "description": "Cadastro e indicadores públicos de uma operadora.",
        "mime_type": "application/json",
    },
    {
        "name": "operadora-regras",
        "uri_template": "tiss://regras/{registro_ans}",
        "description": "Pacote de regras publicado para uma operadora.",
        "mime_type": "application/json",
    },
)


__all__ = ["RESOURCE_DEFINITIONS", "RESOURCE_TEMPLATE_DEFINITIONS"]
