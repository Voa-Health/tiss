# Dados públicos

O stack cria o bucket `voa-tiss-dados`, versionado e com criptografia SSE-S3.
Somente o prefixo `publico/` permite leitura pública.

## Pré-requisitos

Credenciais AWS autorizadas a gerenciar o stack e o bucket, além de
`TISS_CONTA` com o ID da conta de destino.

## Aplicação

```sh
TISS_CONTA=<id-da-conta> bash infra/aplicar.sh dados --dry-run
TISS_CONTA=<id-da-conta> bash infra/aplicar.sh dados
```

Envie o asset da rede usando uma data imutável no caminho:

```sh
aws s3 cp dist/rede/rede-hospitalar.sqlite.gz \
  s3://voa-tiss-dados/publico/rede/<atualizado_em>/rede-hospitalar.sqlite.gz \
  --content-type application/gzip \
  --cache-control "public, max-age=31536000, immutable"
```

Uma versão nova usa uma nova data no caminho.
