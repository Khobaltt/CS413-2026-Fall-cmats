/* Transport and real playback-controller behavior */
import test from 'node:test';
import assert from 'node:assert/strict';
import {createRPC, Player, mount} from '../static/client.mjs';

function fixture(events = [{event:'try',board:[],row:0,column:0}, {event:'solution',board:[1,3,0,2]}, {event:'done'}]) {
  const calls=[], rendered=[]; let index=0, ids=0;
  const rpc=async (method,params) => {
    calls.push({method,params});
    if (method==='queens.open') return {stream_id:`id-${++ids}`,size:params.size};
    if (method==='queens.close') return {closed:true};
    const event=events[index++]; return {events:event?[event]:[],done:!event||event.event==='done'};
  };
  const player=new Player(rpc,event=>rendered.push(event),()=>{},async()=>{});
  return {player,calls,rendered};
}

test('start does not prefetch; step requests one; reset closes and clears', async()=>{
  const {player,calls,rendered}=fixture(); await player.start(4);
  assert.deepEqual(calls.map(x=>x.method),['queens.open']);
  await player.step(); assert.equal(calls[1].params.limit,1);
  assert.equal(rendered.at(-1).event,'try');
  await player.reset(); assert.equal(calls.at(-1).method,'queens.close');
  assert.equal(player.stream,null); assert.equal(player.solutions,0);
});

test('next solution stops at solution; play distinguishes done',async()=>{
  const {player,calls}=fixture(); await player.start(4); await player.run(true);
  assert.equal(player.solutions,1); assert.equal(player.done,false);
  assert.equal(calls.filter(x=>x.method==='queens.next').length,2);
  await player.run(); assert.equal(player.done,true); assert.equal(player.solutions,1);
});

test('pause prevents later requests, including a paused in-flight request',async()=>{
  const {player,calls}=fixture(); let release;
  player.sleep=()=>new Promise(resolve=>release=resolve);
  await player.start(4); const running=player.run();
  while(!release) await new Promise(r=>setImmediate(r));
  player.pause(); release(); await running;
  assert.equal(calls.filter(x=>x.method==='queens.next').length,1);
  assert.equal(player.mode,'idle');
});

test('reset waits for in-flight event then closes old stream',async()=>{
  let release; const calls=[];
  const player=new Player(async(method)=>{
    calls.push(method);
    if(method==='queens.open')return {stream_id:'old'};
    if(method==='queens.next')return new Promise(r=>release=()=>r({events:[{event:'try'}],done:false}));
    return {closed:true};
  },()=>{});
  await player.start(4); const step=player.step(); const reset=player.reset();
  await Promise.resolve(); assert.equal(calls.at(-1),'queens.next');
  release(); await step; await reset;
  assert.equal(calls.at(-1),'queens.close'); assert.equal(player.stream,null);
});

test('transport detects network, HTTP, RPC errors and mismatched IDs',async()=>{
  for(const fetcher of [async()=>{throw Error('offline');}, async()=>({ok:false,status:503}),
    async()=>({ok:true,json:async()=>({jsonrpc:'2.0',id:1,error:{message:'Unavailable'}})}),
    async()=>({ok:true,json:async()=>({jsonrpc:'2.0',id:99,result:{}})})]) {
    await assert.rejects(createRPC(fetcher)('service.health',{}));
  }
});

/* DOM wiring tests with a minimal deterministic DOM double */
class Element {
  constructor(){this.children=[];this.value='8';this.hidden=false;this.disabled=false;this.textContent='';
    this.style={setProperty(){}};this.classList={add(){}};}
  replaceChildren(){this.children=[];} append(x){x.parent=this;this.children.push(x);}
  prepend(x){x.parent=this;this.children.unshift(x);} setAttribute(){}
  get lastChild(){return this.children.at(-1);} remove(){this.parent.children.pop();}
}
function documentDouble(){
  const elements=new Map();return {getElementById(id){if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement(){return new Element();}};
}

test('visible failure and restart control through mounted DOM handlers',async()=>{
  const doc=documentDouble(); const player=mount(doc,async()=>{throw Error('Network unavailable');});
  await doc.getElementById('start').onclick();
  assert.equal(doc.getElementById('error').hidden,false);
  assert.match(doc.getElementById('error').textContent,/Network unavailable.*restart/);
  assert.equal(doc.getElementById('start').disabled,false);
  assert.equal(player.mode,'idle');
});

test('mounted start, step, next solution, completion, reset and speed',async()=>{
  const doc=documentDouble();let i=0;
  const events=[{event:'try',row:0,column:0,board:[]},{event:'solution',board:[1,3,0,2]},{event:'done'}];
  const player=mount(doc,async(method)=>{
    if(method==='queens.open')return {stream_id:'dom'};
    if(method==='queens.close')return {closed:true};
    const event=events[i++];return {events:[event],done:event.event==='done'};
  });
  doc.getElementById('size').value='4'; await doc.getElementById('start').onclick();
  doc.getElementById('speed').value='0';doc.getElementById('speed').oninput();
  assert.equal(player.delay,0);assert.equal(doc.getElementById('board').children.length,16);
  await doc.getElementById('step').onclick(); assert.match(doc.getElementById('status').textContent,/try/);
  await doc.getElementById('next').onclick();assert.equal(doc.getElementById('count').textContent,'1');
  await doc.getElementById('play').onclick();assert.match(doc.getElementById('status').textContent,/Search complete/);
  await doc.getElementById('reset').onclick();assert.equal(player.stream,null);
  assert.equal(doc.getElementById('count').textContent,'0');
});

test('restart recovers when old stream has expired',async()=>{
  const calls=[];
  const player=new Player(async(method)=>{
    calls.push(method);
    if(method==='queens.close'){const error=Error('Stream unavailable');error.code=-32001;throw error;}
    return {stream_id:'new'};
  },()=>{});
  player.stream='expired';await player.start(8);
  assert.equal(player.stream,'new'); assert.deepEqual(calls,['queens.close','queens.open']);
});
