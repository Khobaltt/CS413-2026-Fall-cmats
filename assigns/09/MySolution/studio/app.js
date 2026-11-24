import { StorageAdapter } from "./storage.js";
import { describe, runCases } from "./run.js";

const byId = (id) => document.getElementById(id);
const form = (kind) => byId(`${kind}-form`);
const fields = (kind) => Array.from(form(kind).elements).filter((element) => element.name);
const read = (kind) => Object.fromEntries(fields(kind).map(({ name, value }) => [name, value]));
const selection = (kind) => byId(`${kind}-list`).value;
const setDisabled = (id, value) => { byId(id).disabled = value; };

const editors = {
    program: { adapter: new StorageAdapter("program"), current: null },
    collection: { adapter: new StorageAdapter("collection"), current: null },
};
const base = {};
let caseId = null;
let running = false;

function fill(kind, values = {}) {
    const element = form(kind);
    element.reset();
    for (const field of fields(kind)) {
        if (Object.hasOwn(values, field.name)) field.value = values[field.name];
    }
    base[kind] = JSON.stringify(read(kind));
}

function dirty(kind) {
    return JSON.stringify(read(kind)) !== base[kind];
}

function canDiscard(...kinds) {
    return !kinds.some(dirty) || confirm("Discard unsaved edits?");
}

function showState(kind, loaded) {
    const state = byId(`${kind}-state`);
    const changed = dirty(kind);
    state.dataset.dirty = changed;
    state.textContent = changed ? "Unsaved edits" : loaded ? "Saved" : "New draft";
}

function updateRunButton() {
    setDisabled("run", running || !editors.collection.current?.record.cases.length);
}

function feedback(kind, message = "", isError = false) {
    const element = byId(`${kind}-feedback`);
    element.textContent = message;
    element.dataset.error = isError;
}

function displayError(kind, error) {
    const message = error.code === "revision_conflict"
        ? `Save conflict. The server is at revision ${error.details.current_revision}. Your edits are still here. Use Reload server copy to load the current version.`
        : error.message;
    feedback(kind, message, true);
}

function options(kind, records, currentId) {
    const select = byId(`${kind}-list`);
    select.replaceChildren(new Option("Select an entry", ""));
    for (const { name, id } of records) select.add(new Option(name, id));
    select.value = currentId ?? "";
    setDisabled(`${kind}-open`, !select.value);
}

async function refresh(kind, success = "") {
    const { adapter, current } = editors[kind];
    try {
        options(kind, await adapter.list(), current?.record.id);
        feedback(kind, success);
    } catch (error) {
        feedback(kind, [success, `Could not refresh the list. ${error.message}`].filter(Boolean).join(" "), true);
    }
}

async function perform(kind, operation) {
    const controls = byId(`${kind}-controls`);
    if (controls.disabled) return;
    controls.disabled = true;
    feedback(kind);
    try {
        await operation();
    } catch (error) {
        displayError(kind, error);
    } finally {
        controls.disabled = false;
    }
}

function setCase(record) {
    caseId = record?.id ?? null;
    const expected = record?.expected;
    fill("case", {
        ...(record ?? {}), kind: (expected?.kind === "error" ? expected.category : "value"),
        value: expected?.value ?? "",
    });
    byId("case-list").value = caseId ?? "";
    setDisabled("case-open", !selection("case"));
    setDisabled("case-delete", !caseId);
    updateCaseFields();
}

function updateCaseFields() {
    byId("value-label").hidden = read("case").kind !== "value";
    showState("case", Boolean(caseId));
}

function refreshCases() {
    const record = editors.collection.current?.record;
    byId("case-section").hidden = !record;
    options("case", record?.cases ?? [], caseId);
    updateRunButton();
}

function loadEditor(kind, current, { keepCase = false } = {}) {
    editors[kind].current = current;
    fill(kind, current?.record);
    byId(`${kind}-list`).value = current?.record.id ?? "";
    setDisabled(`${kind}-open`, !selection(kind));
    setDisabled(`${kind}-reload`, !current);
    setDisabled(`${kind}-delete`, !current);
    showState(kind, Boolean(current));
    if (kind === "collection") {
        if (!keepCase) setCase(null);
        refreshCases();
    }
}

for (const [kind, editor] of Object.entries(editors)) {
    const drafts = kind === "collection" ? [kind, "case"] : [kind];
    const open = (id) => {
        if (!id || !canDiscard(...drafts)) return;
        perform(kind, async () => {
            loadEditor(kind, await editor.adapter.get(id));
            await refresh(kind, "Loaded the server copy.");
        });
    };
    loadEditor(kind, null);
    form(kind).addEventListener("input", () => showState(kind, Boolean(editor.current)));
    byId(`${kind}-list`).addEventListener("change", () => setDisabled(`${kind}-open`, !selection(kind)));
    byId(`${kind}-open`).addEventListener("click", () => open(selection(kind)));
    byId(`${kind}-reload`).addEventListener("click", () => open(editor.current?.record.id));
    byId(`${kind}-new`).addEventListener("click", () => {
        if (canDiscard(...drafts)) {
            loadEditor(kind, null);
            feedback(kind);
            form(kind).elements.namedItem("name").focus();
        }
    });
    form(kind).addEventListener("submit", (event) => {
        event.preventDefault();
        const values = read(kind);
        perform(kind, async () => {
            const saved = await editor.adapter.save(values, editor.current);
            loadEditor(kind, saved, { keepCase: Boolean(editor.current) });
            await refresh(kind, "Saved.");
        });
    });
    byId(`${kind}-delete`).addEventListener("click", () => {
        if (!confirm(`Delete this ${kind} and discard any unsaved edits?`)) return;
        perform(kind, async () => {
            await editor.adapter.remove(editor.current);
            loadEditor(kind, null);
            await refresh(kind, "Deleted.");
        });
    });
    perform(kind, () => refresh(kind));
}

const collections = editors.collection;
byId("case-list").addEventListener("change", () => setDisabled("case-open", !selection("case")));
byId("case-open").addEventListener("click", () => {
    if (canDiscard("case")) {
        const selected = selection("case");
        setCase(collections.current.record.cases.find((record) => record.id === selected));
        feedback("collection");
    }
});
byId("case-new").addEventListener("click", () => {
    if (canDiscard("case")) {
        setCase(null);
        feedback("collection");
        form("case").elements.namedItem("name").focus();
    }
});
form("case").addEventListener("input", updateCaseFields);
form("case").addEventListener("submit", (event) => {
    event.preventDefault();
    const { kind, value, ...values } = read("case");
    const expected = kind === "value" ? { kind, value } : { kind: "error", category: kind };
    perform("collection", async () => {
        const editedId = caseId;
        collections.current = await collections.adapter.saveCase(collections.current, editedId, { ...values, expected });
        const cases = collections.current.record.cases;
        setCase(editedId ? cases.find((record) => record.id === editedId) : cases.at(-1));
        refreshCases();
        feedback("collection", "Case saved.");
    });
});
byId("case-delete").addEventListener("click", () => {
    if (!confirm("Delete this case and discard its unsaved edits?")) return;
    perform("collection", async () => {
        collections.current = await collections.adapter.removeCase(collections.current, caseId);
        setCase(null);
        refreshCases();
        feedback("collection", "Case deleted.");
    });
});

byId("run").addEventListener("click", async () => {
    // capture the saved records before any edits or selection changes
    const snapshot = structuredClone(collections.current.record);
    const summary = byId("run-summary");
    const results = byId("results");
    const label = `${snapshot.name} · revision ${snapshot.revision}`;
    let passed = 0;
    running = true;
    updateRunButton();
    results.replaceChildren();
    summary.textContent = `Running ${label}…`;
    try {
        await runCases(snapshot, (result) => {
            passed += Number(result.pass);
            const row = document.createElement("li");
            row.dataset.caseId = result.id;
            row.dataset.pass = result.pass;
            const status = document.createElement("strong");
            status.textContent = result.pass ? "Pass" : "Fail";
            const details = document.createElement("details");
            const title = document.createElement("summary");
            title.textContent = "Source snapshot";
            const source = document.createElement("pre");
            source.textContent = result.source;
            details.append(title, source);
            row.append(status, ` · ${result.name}. Expected ${describe(result.expected)}. Observed ${result.observed}.`, details);
            results.append(row);
        });
        summary.textContent = `${label} · ${passed} of ${snapshot.cases.length} passed`;
    } finally {
        running = false;
        updateRunButton();
    }
});

window.addEventListener("beforeunload", (event) => {
    if (["program", "collection", "case"].some(dirty)) {
        event.preventDefault();
        event.returnValue = "";
    }
});
