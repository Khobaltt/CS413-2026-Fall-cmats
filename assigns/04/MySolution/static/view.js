/* View forwards interactions and renders state; it contains no language tools. */
const $ = id => document.getElementById(id);
let state = null, pending = false, editingRequest = false, chain = Promise.resolve();
function controls() {
  if (!state) return;
  const blocked = pending || state.busy;
  const dirty = $('editor').value !== state.source || state.dirty;
  $('sourceControls').disabled = blocked || dirty;
  $('editor').disabled = state.busy || (pending && !editingRequest);
  $('apply').disabled = blocked || !dirty && state.revision > 0;
  $('discard').disabled = blocked || !dirty;
  document.querySelectorAll('[data-operation]').forEach(b => {
    b.disabled = blocked || dirty || !state.revision || (b.dataset.operation === 'execute' && !state.executable);
  });
}
function render(s, keepEditor = false) {
  state = s;
  if (!keepEditor) $('editor').value = s.draft;
  $('identity').textContent = `Source: ${s.name} | Revision: ${s.revision}${s.dirty ? ' | Unapplied changes' : ''}`;
  $('status').textContent = s.notice;
  $('results').textContent = s.results.map(r => `${r.operation} | revision ${r.revision} | ${r.outcome}\n${r.text}`).join('\n\n');
  controls();
}
async function send(command, data = {}) {
  editingRequest = command === 'edit'; pending = true; controls();
  try {
    const response = await fetch('/api/command', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({command,data})});
    if (!response.ok) throw new Error(`Request failed (${response.status}); source is preserved.`);
    render(await response.json(), command === 'edit');
  } catch (e) { $('status').textContent = e.message; }
  finally { pending = false; editingRequest = false; controls(); }
}
function enqueue(command, data) {
  chain = chain.then(() => send(command, data));
  return chain;
}
$('editor').addEventListener('input', () => {
  // Disable actions immediately; serialize edits before Apply or other requests.
  controls();
  enqueue('edit', {text:$('editor').value});
});
$('apply').onclick = () => enqueue('apply');
$('discard').onclick = () => enqueue('discard');
$('load').onclick = () => {
  const choice = $('sourceMenu').value;
  if (choice === 'file') $('file').click();
  else enqueue(choice === 'manual' ? 'manual' : 'load', {choice});
};
$('file').onchange = async () => {
  const file = $('file').files[0];
  if (!file) return;
  if (file.size > 500000) { $('status').textContent = 'File exceeds 32,768 UTF-8 bytes. Choose a smaller file.'; $('file').value=''; return; }
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary=''; bytes.forEach(x => binary += String.fromCharCode(x));
  enqueue('upload', {name:file.name, bytes:btoa(binary)});
  $('file').value='';
};
document.querySelectorAll('[data-operation]').forEach(b => b.onclick = () => enqueue('action', {operation:b.dataset.operation}));
async function poll() {
  try {
    if (!pending && (!state || state.busy)) {
      const response = await fetch('/api/state');
      render(await response.json());
    }
  } catch(e) { $('status').textContent='Connection failed. Retry when the server is available.'; }
  setTimeout(poll, 100);
}
poll();
