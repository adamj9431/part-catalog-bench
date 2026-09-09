// Dependency-free checks for chart data, keyboard wiring, and sorting.
// Run with: node --test tests/minisite.test.cjs
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
test('landing page has the requested title, callout order and table before chart',()=>{
  const html=fs.readFileSync('site/index.html','utf8');
  assert.ok(html.includes('<h1 id="title">Part Catalog Bench</h1>'));
  assert.ok(html.includes('Example questions from the benchmark'));
  assert.ok(!html.includes('The questions below are the sort of things I wanted help with.'));
  assert.ok(!html.includes('Results so far'));
  assert.ok(!html.includes('id="scope"'));
  const ids=['n-questions','n-exercises','best-score','n-models'];
  for(let i=1;i<ids.length;i++) assert.ok(html.indexOf(`id="${ids[i-1]}"`)<html.indexOf(`id="${ids[i]}"`));
  assert.ok(html.indexOf('id="results"')<html.indexOf('class="panel chart-panel"'));
  assert.ok(!fs.readFileSync('site/app.js','utf8').includes('$("#scope")'));
});
const elements = new Map();
const element = key => {
  if (!elements.has(key)) elements.set(key, {innerHTML:'', textContent:'', value:'by_difficulty',addEventListener(){}});
  return elements.get(key);
};
const context = vm.createContext({
  document:{querySelector:element,querySelectorAll:()=>[]},
  window:{innerWidth:1100,addEventListener(){}},
  fetch:()=>new Promise(()=>{}),setTimeout,clearTimeout,
});
vm.runInContext(fs.readFileSync('site/app.js','utf8'),context);
const rows = JSON.parse(fs.readFileSync('site/data/results.json','utf8')).models;
context.rows=rows;
test('displayed and downloadable citations match and identify Adam Johnson',()=>{
  const html=fs.readFileSync('site/index.html','utf8');
  const displayed=html.match(/<code id="citation-bibtex">([\s\S]*?)<\/code>/)[1];
  assert.equal(displayed.trim(),fs.readFileSync('site/citation.bib','utf8').trim());
  assert.ok(displayed.includes('Johnson, Adam'));
  assert.ok(fs.readFileSync('CITATION.cff','utf8').includes('given-names: Adam'));
});
test('citation copy reports success or a usable fallback',async()=>{
  element('#citation-bibtex').textContent='example citation';
  let copied;
  context.navigator={clipboard:{writeText:async text=>{copied=text;}}};
  await vm.runInContext('copyCitation()',context);
  assert.equal(copied,'example citation');
  assert.equal(element('#citation-status').textContent,'Copied.');
  context.navigator={};
  await vm.runInContext('copyCitation()',context);
  assert.match(element('#citation-status').textContent,/download the .bib file/);
});

test('frontier retains cost-quality tradeoffs and excludes dominated models',()=>{
  const ids=vm.runInContext(`frontier([
    {model:'cheap',cost_usd:2,score:.54},
    {model:'middle',cost_usd:14,score:.61},
    {model:'dominated',cost_usd:15,score:.55},
    {model:'best',cost_usd:16,score:.87}
  ]).map(r=>r.model).join(',')`,context);
  assert.equal(ids,'cheap,middle,best');
});
test('missing costs sort last and cannot enter frontier',()=>{
  const value=vm.runInContext(`(()=>{const a=[{model:'a',cost_usd:null,score:1},{model:'b',cost_usd:2,score:.8},{model:'c',cost_usd:2,score:.7}];return [sortedRows(a,'cost_usd',-1).at(-1).model,frontier(a).map(r=>r.model).join(',')].join('|')})()`,context);
  assert.equal(value,'a|b');
});
test('desktop and mobile charts produce finite geometry and accessible points',()=>{
  for(const compact of [true,false]){
    const svg=vm.runInContext(`chartMarkup(rows,${compact})`,context);
    assert.ok(svg.startsWith('<svg'));
    assert.ok(!/NaN|Infinity|undefined/.test(svg));
    const pricedRows = rows.filter(r => Number.isFinite(r.cost_usd) && r.cost_usd > 0);
    assert.equal((svg.match(/data-point=/g)||[]).length,pricedRows.length);
    assert.ok(svg.includes('tabindex="0" role="button"'));
  }
});
test('dynamic markup escapes model names',()=>{
  assert.equal(vm.runInContext(`esc('<script>"&')`,context),'&lt;script&gt;&quot;&amp;');
});
test('selection and both breakdowns render aggregate-only views',()=>{
  vm.runInContext('data={models:rows};selectModel(rows[0].model)',context);
  assert.ok(element('#leaderboard').innerHTML.includes('GPT-6 Astra'));
  assert.ok(!element('#leaderboard').innerHTML.includes('<small>openrouter</small>'));
  assert.ok(element('#model-id').textContent.includes('openrouter'));
  assert.ok(fs.readFileSync('site/index.html','utf8').includes('These models were accessed through OpenRouter.'));
  assert.ok(element('#bars').innerHTML.includes('Easy'));
  element('#breakdown').value='by_category';
  vm.runInContext('renderDetails()',context);
  assert.ok(element('#bars').innerHTML.includes('Part identification'));
  assert.ok(!element('#bars').innerHTML.includes('Quantities'));
});
