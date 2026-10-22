# Serverless TODO — AWS サーバーレス ハンズオン

フロントエンドもバックエンドも AWS のサーバーレスサービスで動く TODO アプリです。
初心者が **AWS マネジメントコンソール（GUI）** で手を動かしながら、AWS SAA（ソリューションアーキテクト – アソシエイト）レベルの知識を身につけることを目的としています。

📖 **ハンズオン記事: [docs/handson.md](docs/handson.md)**（所要時間 **約 60 分**。アカウント準備などの事前準備を除く）

| パート | 目安 |
| --- | --- |
| 完成イメージとアーキテクチャ・基礎知識 | 10 分 |
| Step 1：DynamoDB でテーブルを作る | 5 分 |
| Step 2：Lambda で API の処理を作る | 10 分 |
| Step 3：IAM で Lambda に DynamoDB へのアクセスを許可する | 5 分 |
| Step 4：API Gateway で API を公開する | 7 分 |
| Step 5：S3 にフロントエンドのファイルを置く | 5 分 |
| Step 6：CloudFront で入口を 1 つにまとめる | 10 分 |
| Step 7：ブラウザで動作確認する | 3 分 |
| 後片付け | 5 分 |

コマンドラインのツールは不要です。ブラウザだけで完結します。

## アーキテクチャ

![Serverless TODO のアーキテクチャ図](docs/images/architecture.png)

1. ブラウザから CloudFront に HTTPS でアクセス（入口はここ 1 か所だけ）
2. `/api/*` 以外は S3 から HTML / CSS / JS を取得（OAC で署名。S3 は非公開のまま）
3. `/api/*` は API Gateway へ転送（キャッシュしない）
4. API Gateway が Lambda を呼び出す
5. Lambda が DynamoDB を読み書きする
6. Lambda のログを CloudWatch Logs に出力

<sub>※ アイコンは [AWS Architecture Icons](https://aws.amazon.com/jp/architecture/icons/) を使用しています。</sub>

| レイヤー | サービス |
| --- | --- |
| フロントエンド配信 | Amazon S3（非公開）+ Amazon CloudFront（OAC） |
| API | Amazon API Gateway（HTTP API） |
| ロジック | AWS Lambda（Python 3.13 / arm64） |
| データ | Amazon DynamoDB（オンデマンド） |
| 権限 | AWS IAM（実行ロール + リソースベースポリシー） |
| ログ | Amazon CloudWatch Logs |
| 構築方法 | マネジメントコンソール（本編）／ AWS SAM による IaC（付録） |

## ディレクトリ構成

```text
.
├── backend/
│   ├── src/lambda_function.py       # ★ Lambda 関数（TODO API）。コンソールに貼り付ける
│   └── tests/                       # ユニットテスト（moto で DynamoDB をモック）
├── frontend/                        # ★ 静的サイト（HTML / CSS / JS、ビルド不要）。S3 にアップロードする
├── docs/
│   ├── handson.md                   # ハンズオン記事
│   └── images/                      # アーキテクチャ図（PNG / SVG）
├── template.yaml                    # 同じ構成の IaC 定義（AWS SAM）。付録で使用
└── scripts/
    ├── deploy-frontend.sh           # SAM 版：S3 へのアップロード + CloudFront キャッシュ削除
    └── cleanup.sh                   # SAM 版：全リソースの削除
```

本編（コンソール）で使うのは ★ の付いたファイルだけです。

## おまけ：AWS SAM でコマンド一発構築

本編と同じ構成を、IaC（AWS SAM）で構築することもできます。詳しくは [ハンズオン記事の付録 D](docs/handson.md#付録-d同じ構成を-aws-samiacで一発構築する) を参照してください。

前提: AWS CLI v2・AWS SAM CLI・Python 3.13 がインストール済みで、AWS の認証情報が設定されていること。

```bash
# テスト（AWS アカウント不要）
cd backend && python3.13 -m venv .venv && source .venv/bin/activate
pip install -r tests/requirements.txt && pytest -v
deactivate && cd ..

# バックエンド + インフラのデプロイ（スタック名は serverless-todo、リージョンは ap-northeast-1）
sam build
sam deploy --guided

# フロントエンドのデプロイ
./scripts/deploy-frontend.sh

# 後片付け
./scripts/cleanup.sh
```

## API

| メソッド | パス | 説明 |
| --- | --- | --- |
| GET | `/api/todos` | 一覧を取得 |
| POST | `/api/todos` | 作成（`{"title": "..."}`） |
| PUT | `/api/todos/{id}` | 更新（`{"title": "..."}` / `{"done": true}`） |
| DELETE | `/api/todos/{id}` | 削除 |
