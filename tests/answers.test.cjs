const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function page(example) {
  const nodes = new Map();
  const get = key => {
    if (!nodes.has(key)) nodes.set(key, {hidden:true,innerHTML:'',textContent:'',style:{},events:{},
      addEventListener(event,fn){this.events[event]=fn;}});
    return nodes.get(key);
  };
  const context=vm.createContext({URLSearchParams,location:{search:`?example=${example}`},
    document:{querySelector:get}});
  vm.runInContext(fs.readFileSync('site/answer.js','utf8'),context);
  return {get,context};
}

test('all three answer routes render their answer and highlights',()=>{
  for(const key of ['attachment','hardware','assembly']){
    const {get}=page(key);
    assert.equal(get('#answer-content').hidden,false);
    assert.ok(get('#answer-highlights').innerHTML.includes('non-scaling-stroke'));
    assert.ok(get('#answer-markers').innerHTML.includes('href="#step-'));
    assert.ok(get('#correct-answer').innerHTML.length>0);
    assert.ok(!get('#answer-highlights').innerHTML.includes('undefined'));
    get('#diagram-zoom').events.change({target:{value:'2'}});
    assert.equal(get('#annotated-diagram').style.width,'200%');
  }
});
test('assembly answer preserves all thirteen positions and repeated parts',()=>{
  const {context}=page('assembly');
  assert.equal(vm.runInContext('example.parts.length',context),13);
  assert.equal(vm.runInContext('example.parts.filter(p=>p==="371169-S").length',context),4);
  assert.equal(vm.runInContext('example.parts.includes("5495")',context),false);
});
test('each offset marker has a thin connector to its highlighted region',()=>{
  for (const key of ['attachment','hardware','assembly']) {
    const {get,context}=page(key);
    const regions=vm.runInContext('example.regions',context);
    assert.equal((get('#answer-highlights').innerHTML.match(/class="diagram-leader /g)||[]).length,regions.length);
    for (const r of regions) {
      assert.ok(Math.hypot(r.marker[0]-r.target[0],r.marker[1]-r.target[1])>=48);
      assert.ok([...r.marker,...r.target].every(Number.isFinite));
    }
  }
});
test('attachment uses close-fitting part outlines and a separate assembly-line box',()=>{
  const {get,context}=page('attachment');
  const regions=vm.runInContext('example.regions',context);
  assert.equal(new Set(regions.map(r=>r.tone)).size,4);
  assert.equal(regions.map(r=>r.label).join(','),'1,2,3,4');
  assert.ok(regions.filter(r=>r.label!=='3').every(r=>!r.rect && (r.path || r.polygon)));
  assert.equal(regions[2].title,'Assembly guide line');
  assert.ok(regions[2].rect[2]<=10 && regions[2].rect[3]>200);
  assert.equal((regions[1].path.match(/M /g)||[]).length,2);
  for (const r of regions) {
    for (const node of ['#answer-highlights','#answer-markers','#answer-steps']) {
      assert.ok(get(node).innerHTML.includes(`tone-${r.tone}`));
    }
  }
});
test('unrecognized example shows an error and never interprets supplied HTML',()=>{
  for (const key of ['not-a-question', 'toString', '__proto__']) {
    const {get}=page(key);
    assert.equal(get('#answer-error').hidden,false);
    assert.equal(get('#answer-content').hidden,true);
  }
});
test('other examples use matching colors, individual part outlines and an unscored guide',()=>{
  for (const key of ['hardware','assembly']) {
    const {get,context}=page(key);
    const regions=vm.runInContext('example.regions',context);
    assert.equal(new Set(regions.map(r=>r.tone)).size,regions.length);
    assert.ok(regions.every(r=>r.path || r.polygon));
    for (const r of regions) for (const node of ['#answer-highlights','#answer-markers','#answer-steps']) {
      assert.ok(get(node).innerHTML.includes(`tone-${r.tone}`));
    }
  }
  const {get,context}=page('assembly');
  assert.equal(vm.runInContext('example.regions.filter(r=>r.guide).length',context),1);
  assert.equal(vm.runInContext('example.parts.join(",")',context),'378866-S,371169-S,55490,5482,55490,371169-S,5490,371169-S,55490,3397,5A491,55490,371169-S');
  assert.ok(get('#correct-answer').innerHTML.includes('lower control arm'));
  assert.ok(get('#answer-highlights').innerHTML.includes('assembly-guide'));
});
