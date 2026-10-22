#!/usr/bin/env bash
# フロントエンド（frontend/ 配下）を S3 にアップロードし、CloudFront のキャッシュを削除する
#
# 使い方: ./scripts/deploy-frontend.sh [スタック名]   (省略時: serverless-todo)
set -euo pipefail

STACK_NAME="${1:-serverless-todo}"
cd "$(dirname "$0")/.."

# CloudFormation スタックの出力（Outputs）から値を取り出す
output() {
  aws cloudformation describe-stacks --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}

BUCKET=$(output FrontendBucketName)
DISTRIBUTION_ID=$(output DistributionId)
WEBSITE_URL=$(output WebsiteUrl)

echo "==> frontend/ を s3://${BUCKET} にアップロードします"
aws s3 sync frontend/ "s3://${BUCKET}" --delete

echo "==> CloudFront (${DISTRIBUTION_ID}) のキャッシュを削除します"
aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths "/*" \
  --query "Invalidation.Id" --output text

echo
echo "完了しました。ブラウザで開いてください: ${WEBSITE_URL}"
