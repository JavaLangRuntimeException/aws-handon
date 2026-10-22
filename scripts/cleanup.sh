#!/usr/bin/env bash
# ハンズオンで作成したリソースをすべて削除する
#
# 使い方: ./scripts/cleanup.sh [スタック名]   (省略時: serverless-todo)
set -euo pipefail

STACK_NAME="${1:-serverless-todo}"

BUCKET=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" --output text)

# 中身が残っている S3 バケットは CloudFormation から削除できないため、先に空にする
echo "==> s3://${BUCKET} を空にします"
aws s3 rm "s3://${BUCKET}" --recursive

echo "==> スタック ${STACK_NAME} を削除します"
sam delete --stack-name "$STACK_NAME"
