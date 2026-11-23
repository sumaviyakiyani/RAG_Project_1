// Talks to the FastAPI backend (same origin). All text is inserted with textContent (no XSS).
const $ = (id) => document.getElementById(id);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function api(path, options) {
  const res = await fetch(path, options);
  if (res.status === 204) return null;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`${res.status} ${body.error?.code || ""}: ${body.error?.message || "Request failed"}`);
  return body;
}

async function loadDocs() {
  const docs = await api("/documents");
  const list = $("docs");
  list.replaceChildren();
  $("docs-empty").hidden = docs.length > 0;
  for (const d of docs) {
    const li = el("li");
    const info = el("div");
    info.append(el("div", "name", d.filename), el("div", "meta", `${d.page_count} pages/sections, ${d.chunk_count} chunks`));
    const del = el("button", "danger", "Delete");
    del.setAttribute("aria-label", `Delete ${d.filename}`);
    del.onclick = async () => {
      del.disabled = true;
      let deleteError;
      try { await api(`/documents/${d.doc_id}`, { method: "DELETE" }); }
      catch (e) { deleteError = e; }

      if (!deleteError) {
        li.remove();
        $("docs-empty").hidden = $("docs").children.length > 0;
      }

      try { await loadDocs(); }
      catch (refreshError) {
        const message = deleteError
          ? `${deleteError.message}; failed to refresh document list: ${refreshError.message}`
          : `Deleted ${d.filename}, but failed to refresh document list: ${refreshError.message}`;
        setStatus(message, false);
        del.disabled = false;
        return;
      }

      if (deleteError) setStatus(deleteError.message, false);
      else setStatus(`Deleted ${d.filename}`, true);
      del.disabled = false;
    };
    li.append(info, del);
    list.append(li);
  }
}

function setStatus(message, ok) {
  const s = $("upload-status");
  s.textContent = message;
  s.className = ok ? "ok" : "bad";
}

$("file").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  setStatus(`Uploading ${file.name}...`, true);
  try {
    const d = await api("/documents", { method: "POST", body: form });
    setStatus(`Uploaded ${d.filename} (${d.chunk_count} chunks)`, true);
  } catch (err) { setStatus(err.message, false); }
  e.target.value = "";
  loadDocs();
});

function renderAnswer(r) {
  const box = el("div", "a" + (r.answerable ? "" : " refused"));
  box.append(el("div", "text", r.answer));
  if (r.citations.length) {
    const ul = el("ul", "cites");
    for (const c of r.citations) ul.append(el("li", "", `[${c.source_number}] ${c.filename}, ${c.location}`));
    box.append(ul);
  }
  const det = el("details");
  det.open = true;
  det.append(el("summary", "", `Retrieved chunks: ${r.total_retrieved} retrieved, ${r.retrieved_chunks.filter(c => c.used_in_context).length} sent to the model`));
  for (const c of r.retrieved_chunks) {
    const card = el("div", "chunk" + (c.used_in_context ? "" : " unused"));
    const bar = el("div", "bar"); const fill = el("i"); fill.style.width = `${Math.max(0, Math.min(1, c.score)) * 100}%`; bar.append(fill);
    const head = el("div", "head");
    head.append(
      el("span", "", c.source_number ? `Source [${c.source_number}]` : "Below threshold, not used"),
      el("span", "", `Score ${c.score.toFixed(3)}`),
      el("span", "", c.filename), el("span", "", c.location),
      el("span", "", `Chunk ${c.chunk_id}`));
    card.append(head, bar, el("p", "", c.text));
    det.append(card);
  }
  box.append(det);
  return box;
}

$("ask-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("question").value.trim();
  if (!q) return;
  const chat = $("chat");
  chat.append(el("div", "q", q));
  $("question").value = "";
  $("ask-btn").disabled = true;
  try {
    const r = await api("/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q }) });
    chat.append(renderAnswer(r));
  } catch (err) { chat.append(el("div", "a error", err.message)); }
  $("ask-btn").disabled = false;
  chat.lastElementChild.scrollIntoView({ behavior: "smooth", block: "nearest" });
});

loadDocs().catch((e) => setStatus(e.message, false));
