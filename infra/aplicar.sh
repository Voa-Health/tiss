#!/usr/bin/env bash
set -euo pipefail

CONTA_ESPERADA="${TISS_CONTA:?defina TISS_CONTA com o ID da conta AWS de destino}"
REGIAO="${AWS_REGION:-sa-east-1}"
DIRETORIO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "uso: bash infra/aplicar.sh <nome> [--dry-run]" >&2
  exit 64
fi

NOME="$1"
if [[ ! "$NOME" =~ ^[a-z0-9-]+$ ]]; then
  echo "uso: bash infra/aplicar.sh <nome> [--dry-run]" >&2
  exit 64
fi

DRY_RUN=false
if [[ $# -eq 2 ]]; then
  if [[ "$2" != "--dry-run" ]]; then
    echo "uso: bash infra/aplicar.sh <nome> [--dry-run]" >&2
    exit 64
  fi
  DRY_RUN=true
fi

TEMPLATE="$DIRETORIO/$NOME.yaml"
if [[ ! -f "$TEMPLATE" ]]; then
  echo "template não encontrado: $TEMPLATE" >&2
  exit 66
fi

STACK="voa-tiss-prod-$NOME"

export AWS_DEFAULT_REGION="$REGIAO"
export AWS_REGION="$REGIAO"

# A conta errada poderia aceitar a criação dos recursos em outro ambiente.
CONTA="$(aws sts get-caller-identity --query Account --output text --region "$REGIAO")"
if [[ "$CONTA" != "$CONTA_ESPERADA" ]]; then
  echo "ABORTADO: conta AWS $CONTA; esperada $CONTA_ESPERADA." >&2
  exit 78
fi

if [[ "$DRY_RUN" == true ]]; then
  if ESTADO="$(aws cloudformation describe-stacks --stack-name "$STACK" \
    --region "$REGIAO" --query 'Stacks[0].StackStatus' --output text 2>&1)"; then
    # Um dry-run anterior deixa o stack novo em REVIEW_IN_PROGRESS.
    TIPO="UPDATE"
    [[ "$ESTADO" == "REVIEW_IN_PROGRESS" ]] && TIPO="CREATE"
  elif [[ "$ESTADO" == *"does not exist"* ]]; then
    TIPO="CREATE"
  else
    echo "$ESTADO" >&2
    exit 1
  fi

  CHANGE_SET="preview-${NOME}-$(date -u +%Y%m%d%H%M%S)"
  aws cloudformation create-change-set \
    --stack-name "$STACK" \
    --change-set-name "$CHANGE_SET" \
    --change-set-type "$TIPO" \
    --template-body "file://$TEMPLATE" \
    --region "$REGIAO" >/dev/null

  if ! aws cloudformation wait change-set-create-complete \
    --stack-name "$STACK" --change-set-name "$CHANGE_SET" --region "$REGIAO"; then
    aws cloudformation describe-change-set \
      --stack-name "$STACK" --change-set-name "$CHANGE_SET" --region "$REGIAO" \
      --output json
    exit 1
  fi

  aws cloudformation describe-change-set \
    --stack-name "$STACK" --change-set-name "$CHANGE_SET" --region "$REGIAO" \
    --output json
  exit 0
fi

aws cloudformation deploy \
  --stack-name "$STACK" \
  --template-file "$TEMPLATE" \
  --region "$REGIAO" \
  --no-fail-on-empty-changeset
