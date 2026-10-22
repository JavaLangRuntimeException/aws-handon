"""Lambda 関数のユニットテスト

moto を使って DynamoDB をメモリ上にモックするので、AWS アカウントがなくても実行できます。

    cd backend
    pip install -r tests/requirements.txt
    pytest -v
"""

import importlib
import json
import os
import sys

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

TABLE_NAME = "todo-test"


@pytest.fixture
def app():
    os.environ["TABLE_NAME"] = TABLE_NAME
    os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-1"
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"

    with mock_aws():
        boto3.client("dynamodb").create_table(
            TableName=TABLE_NAME,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        )
        # lambda_function.py はインポート時にテーブルへの参照を作るので、モック開始後に読み込み直す
        import lambda_function as app_module

        yield importlib.reload(app_module)


def call(app, route_key, body=None, todo_id=None):
    event = {"routeKey": route_key}
    if body is not None:
        event["body"] = json.dumps(body)
    if todo_id is not None:
        event["pathParameters"] = {"id": todo_id}
    res = app.lambda_handler(event, None)
    return res["statusCode"], json.loads(res["body"]) if "body" in res else None


def test_create_and_list(app):
    status, created = call(app, "POST /api/todos", {"title": "  牛乳を買う  "})
    assert status == 201
    assert created["title"] == "牛乳を買う"
    assert created["done"] is False

    status, body = call(app, "GET /api/todos")
    assert status == 200
    assert [item["id"] for item in body["items"]] == [created["id"]]


def test_update(app):
    _, created = call(app, "POST /api/todos", {"title": "洗濯"})

    status, updated = call(app, "PUT /api/todos/{id}", {"done": True}, created["id"])
    assert status == 200
    assert updated["done"] is True
    assert updated["title"] == "洗濯"


def test_delete(app):
    _, created = call(app, "POST /api/todos", {"title": "掃除"})

    status, _ = call(app, "DELETE /api/todos/{id}", todo_id=created["id"])
    assert status == 204

    _, body = call(app, "GET /api/todos")
    assert body["items"] == []


def test_update_and_delete_unknown_id_returns_404(app):
    status, _ = call(app, "PUT /api/todos/{id}", {"done": True}, "no-such-id")
    assert status == 404

    status, _ = call(app, "DELETE /api/todos/{id}", todo_id="no-such-id")
    assert status == 404


@pytest.mark.parametrize(
    "body",
    [{}, {"title": ""}, {"title": "   "}, {"title": 123}, {"title": "a" * 101}],
)
def test_create_rejects_invalid_title(app, body):
    status, res = call(app, "POST /api/todos", body)
    assert status == 400
    assert "title" in res["message"]


def test_invalid_json_returns_400(app):
    res = app.lambda_handler({"routeKey": "POST /api/todos", "body": "{broken"}, None)
    assert res["statusCode"] == 400


def test_unknown_route_returns_404(app):
    status, _ = call(app, "PATCH /api/todos")
    assert status == 404
