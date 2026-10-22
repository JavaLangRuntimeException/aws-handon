// フロントエンドと API は同じ CloudFront ドメインで配信されるため、相対パスで呼び出せる。
// （CloudFront のビヘイビアで /api/* だけを API Gateway に振り分けている）
const API_BASE = "/api";

const form = document.getElementById("todo-form");
const input = document.getElementById("todo-input");
const list = document.getElementById("todo-list");
const empty = document.getElementById("empty");
const count = document.getElementById("count");
const message = document.getElementById("message");

let todos = [];

// ---------- API 呼び出し ----------

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 204) return null;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.message || `HTTP ${res.status}`);
  }
  return data;
}

const api = {
  list: () => request("/todos"),
  create: (title) => request("/todos", { method: "POST", body: JSON.stringify({ title }) }),
  update: (id, fields) => request(`/todos/${id}`, { method: "PUT", body: JSON.stringify(fields) }),
  remove: (id) => request(`/todos/${id}`, { method: "DELETE" }),
};

// ---------- 画面描画 ----------

function render() {
  list.replaceChildren(...todos.map(renderItem));
  empty.hidden = todos.length > 0;

  const remaining = todos.filter((t) => !t.done).length;
  count.textContent = todos.length ? `残り ${remaining} 件 / 全 ${todos.length} 件` : "";
}

function renderItem(todo) {
  const li = document.createElement("li");
  li.className = `todo-item${todo.done ? " done" : ""}`;

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = todo.done;
  checkbox.setAttribute("aria-label", "完了");
  checkbox.addEventListener("change", () => toggleTodo(todo, checkbox.checked));

  // ユーザー入力は textContent で埋め込む（innerHTML を使うと XSS の原因になる）
  const title = document.createElement("span");
  title.className = "title";
  title.textContent = todo.title;

  const del = document.createElement("button");
  del.className = "delete";
  del.textContent = "削除";
  del.addEventListener("click", () => deleteTodo(todo));

  li.append(checkbox, title, del);
  return li;
}

function showError(err) {
  message.textContent = `エラー: ${err.message}`;
  message.hidden = false;
}

function clearError() {
  message.hidden = true;
}

// ---------- 操作 ----------

async function loadTodos() {
  try {
    const data = await api.list();
    todos = data.items;
    render();
    clearError();
  } catch (err) {
    showError(err);
  }
}

async function addTodo(title) {
  const button = form.querySelector("button");
  button.disabled = true;
  try {
    const created = await api.create(title);
    todos.push(created);
    render();
    clearError();
    input.value = "";
  } catch (err) {
    showError(err);
  } finally {
    button.disabled = false;
    input.focus();
  }
}

async function toggleTodo(todo, done) {
  try {
    const updated = await api.update(todo.id, { done });
    todos = todos.map((t) => (t.id === updated.id ? updated : t));
    clearError();
  } catch (err) {
    showError(err);
  }
  render();
}

async function deleteTodo(todo) {
  try {
    await api.remove(todo.id);
    todos = todos.filter((t) => t.id !== todo.id);
    render();
    clearError();
  } catch (err) {
    showError(err);
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const title = input.value.trim();
  if (title) addTodo(title);
});

loadTodos();
