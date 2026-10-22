"""TODO API (AWS Lambda + Amazon DynamoDB)

API Gateway (HTTP API) から呼び出される Lambda 関数です。
1 つの関数で以下 4 つのルートを処理します。

    GET    /api/todos        TODO 一覧を取得
    POST   /api/todos        TODO を作成
    PUT    /api/todos/{id}   TODO を更新（タイトル / 完了フラグ）
    DELETE /api/todos/{id}   TODO を削除
"""

import base64
import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

# boto3 のクライアントはハンドラーの外で生成する。
# Lambda の実行環境は再利用されるため、2 回目以降の呼び出し（ウォームスタート）で
# 接続の初期化コストを省略できる。
TABLE_NAME = os.environ["TABLE_NAME"]
table = boto3.resource("dynamodb").Table(TABLE_NAME)

MAX_TITLE_LENGTH = 100


def lambda_handler(event, context):
    # HTTP API（ペイロード形式 2.0）では "GET /api/todos" のような routeKey が渡される
    route_key = event.get("routeKey", "")
    path_params = event.get("pathParameters") or {}

    try:
        if route_key == "GET /api/todos":
            return list_todos()
        if route_key == "POST /api/todos":
            return create_todo(parse_body(event))
        if route_key == "PUT /api/todos/{id}":
            return update_todo(path_params.get("id"), parse_body(event))
        if route_key == "DELETE /api/todos/{id}":
            return delete_todo(path_params.get("id"))
        return response(404, {"message": "Not Found"})
    except ValueError as e:
        return response(400, {"message": str(e)})
    except Exception:
        # 想定外のエラーは CloudWatch Logs にスタックトレースを残し、
        # クライアントには詳細を返さない
        print(f"Unhandled error. routeKey={route_key}")
        raise


def list_todos():
    # Scan はテーブル全件を読み込む操作。データ量が増えると遅く・高くなるため、
    # 本番では Query（キー指定の検索）を使える設計にするのが基本。
    # 今回は学習用の小さなアプリなので Scan で済ませている。
    items = []
    kwargs = {}
    while True:
        result = table.scan(**kwargs)
        items.extend(result.get("Items", []))
        if "LastEvaluatedKey" not in result:
            break
        # 1 回の Scan で返るのは最大 1MB まで。続きがあればページングする
        kwargs["ExclusiveStartKey"] = result["LastEvaluatedKey"]

    items.sort(key=lambda item: item["createdAt"])
    return response(200, {"items": items})


def create_todo(body):
    title = validate_title(body.get("title"))
    now = now_iso()
    item = {
        "id": str(uuid.uuid4()),
        "title": title,
        "done": False,
        "createdAt": now,
        "updatedAt": now,
    }
    table.put_item(Item=item)
    return response(201, item)


def update_todo(todo_id, body):
    if not todo_id:
        raise ValueError("id is required")

    updates = {}
    if "title" in body:
        updates["title"] = validate_title(body["title"])
    if "done" in body:
        if not isinstance(body["done"], bool):
            raise ValueError("done must be a boolean")
        updates["done"] = body["done"]
    if not updates:
        raise ValueError("title or done is required")
    updates["updatedAt"] = now_iso()

    # "SET #title = :title, #done = :done, ..." の形の更新式を組み立てる。
    # 属性名はプレースホルダー（#xxx）経由にして DynamoDB の予約語と衝突しないようにする
    update_expression = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
    try:
        result = table.update_item(
            Key={"id": todo_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames={f"#{k}": k for k in updates},
            ExpressionAttributeValues={f":{k}": v for k, v in updates.items()},
            # 存在しない id に対して update_item を呼ぶと新規作成されてしまうため、条件を付ける
            ConditionExpression="attribute_exists(id)",
            ReturnValues="ALL_NEW",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(404, {"message": "Todo not found"})
        raise
    return response(200, result["Attributes"])


def delete_todo(todo_id):
    if not todo_id:
        raise ValueError("id is required")
    try:
        table.delete_item(
            Key={"id": todo_id},
            ConditionExpression="attribute_exists(id)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(404, {"message": "Todo not found"})
        raise
    return response(204)


# ---------- ヘルパー ----------


def parse_body(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("Request body must be valid JSON")
    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object")
    return body


def validate_title(title):
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title is required")
    title = title.strip()
    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError(f"title must be {MAX_TITLE_LENGTH} characters or less")
    return title


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def response(status_code, body=None):
    res = {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
    }
    if body is not None:
        res["body"] = json.dumps(body, ensure_ascii=False)
    return res
