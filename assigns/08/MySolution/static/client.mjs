/* JSON-RPC transport independent of playback and rendering */
export function createRPC(fetcher = globalThis.fetch) {
  let id = 0;
  return async (method, params) => {
    const requestId = ++id;
    const response = await fetcher('/rpc', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({jsonrpc: '2.0', method, params, id: requestId})
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const body = await response.json();
    if (body.jsonrpc !== '2.0' || body.id !== requestId) throw new Error('Invalid RPC response');
    if (body.error) {
      const error = new Error(body.error.message || 'RPC error');
      error.code = body.error.code; throw error;
    }
    return body.result;
  };
}

/* Incremental playback with serialized lifecycle operations */
export class Player {
  constructor(rpc, render, notify = () => {}, sleep = ms => new Promise(r => setTimeout(r, ms))) {
    Object.assign(this, {rpc, render, notify, sleep});
    this.stream = null; this.done = false; this.solutions = 0;
    this.mode = 'idle'; this.generation = 0; this.pending = Promise.resolve();
    this.delay = 150; this.busy = false;
  }
  pause() { this.generation++; this.mode = 'idle'; this.notify(); }
  async settle() { this.pause(); await this.pending.catch(() => {}); }
  async reset() {
    await this.settle();
    if (this.stream) {
      try { await this.rpc('queens.close', {stream_id: this.stream}); }
      catch (error) { if (error.code !== -32001) throw error; }
    }
    this.stream = null; this.done = false; this.solutions = 0;
    this.render(null); this.notify();
  }
  async start(size) {
    await this.reset();
    const result = await this.rpc('queens.open', {size});
    this.stream = result.stream_id; this.notify();
  }
  async step() {
    if (!this.stream || this.done || this.busy) return null;
    this.busy = true; this.notify();
    const operation = (async () => {
      const result = await this.rpc('queens.next', {stream_id: this.stream, limit: 1});
      this.done = result.done;
      const event = result.events[0] || null;
      if (event?.event === 'solution') this.solutions++;
      if (event) this.render(event);
      return event;
    })();
    this.pending = operation;
    try { return await operation; }
    finally { this.busy = false; this.notify(); }
  }
  async run(untilSolution = false) {
    if (!this.stream || this.done || this.mode !== 'idle') return;
    this.mode = untilSolution ? 'solution' : 'play';
    const token = ++this.generation; this.notify();
    try {
      while (token === this.generation && !this.done) {
        const event = await this.step();
        if (untilSolution && event?.event === 'solution') break;
        if (token !== this.generation || this.done) break;
        await this.sleep(this.delay);
      }
    } finally {
      if (token === this.generation) { this.mode = 'idle'; this.notify(); }
    }
  }
}

/* DOM rendering and visible failure recovery */
export function mount(document, rpc = createRPC()) {
  const get = id => document.getElementById(id);
  let size = Number(get('size').value), working = false;
  let lastStatus = 'Ready. Start a search to begin.';
  const describe = event => {
    if (event.event === 'done') return 'Search complete. No further solutions remain.';
    if (event.event === 'solution') return 'Solution found. Continue to explore the remaining search.';
    return `${event.event}: row ${event.row}, column ${event.column}`;
  };
  function render(event) {
    const board = get('board'); board.replaceChildren();
    board.style.setProperty('--size', size);
    board.className = event?.event === 'solution' ? 'solution' : '';
    const queens = event?.board || [];
    for (let row = 0; row < size; row++) for (let column = 0; column < size; column++) {
      const cell = document.createElement('div');
      cell.className = `cell ${(row + column) % 2 ? 'dark' : ''}`;
      cell.textContent = queens[row] === column ? '♛' : '';
      if (event && event.row === row && event.column === column) {
        cell.classList.add(event.event);
        if (event.event === 'try') cell.textContent = '♛';
        if (event.event === 'reject') cell.textContent = '×';
        if (event.event === 'backtrack') cell.textContent = '↶';
      }
      board.append(cell);
    }
    board.setAttribute('aria-label', `${size} by ${size} board; columns by row: ${queens.join(', ') || 'empty'}`);
    lastStatus = event ? describe(event) : 'Ready. Start a search to begin.';
    get('status').textContent = lastStatus;
    if (!event) get('log').replaceChildren();
    else {
      const entry = document.createElement('li'); entry.textContent = lastStatus;
      get('log').prepend(entry);
      while (get('log').children.length > 30) get('log').lastChild.remove();
    }
  }
  function notify() {
    get('count').textContent = String(player.solutions);
    get('play').textContent = player.mode !== 'idle' ? 'Pause' : 'Play';
    const unavailable = working || !player.stream || player.done;
    get('step').disabled = unavailable || player.busy || player.mode !== 'idle';
    get('next').disabled = unavailable || player.busy || player.mode !== 'idle';
    get('play').disabled = unavailable;
    get('start').disabled = working;
    get('reset').disabled = working;
    get('size').disabled = working || Boolean(player.stream);
  }
  const player = new Player(rpc, render, notify);
  const action = fn => async () => {
    if (working) return;
    get('error').hidden = true;
    try { await fn(); }
    catch (error) {
      player.pause();
      get('error').textContent = `${error.message}. Use Start to restart the search.`;
      get('error').hidden = false;
    }
    notify();
  };
  const lifecycle = fn => action(async () => {
    working = true; notify();
    try { await fn(); }
    finally { working = false; notify(); }
  });
  get('start').onclick = lifecycle(async () => {
    size = Number(get('size').value); await player.start(size);
    lastStatus = 'Search opened. Step or play to explore.'; get('status').textContent = lastStatus;
  });
  get('reset').onclick = lifecycle(() => player.reset());
  get('step').onclick = action(() => player.step());
  get('play').onclick = action(() => player.mode === 'idle' ? player.run() : player.pause());
  get('next').onclick = action(() => player.run(true));
  get('size').onchange = () => { size = Number(get('size').value); render(null); };
  get('speed').oninput = () => {
    player.delay = Number(get('speed').value); get('speed-value').textContent = `${player.delay} ms`;
  };
  render(null); notify(); return player;
}
if (typeof document !== 'undefined') mount(document);
