// Dependency-free checks for chart data, keyboard wiring, and sorting.
// Run with: node --test tests/minisite.test.cjs
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
test('catalog description and purchase link are part of the methodology introduction',()=>{
  const html=fs.readFileSync('site/index.html','utf8');
  const section=html.match(/<section id="methodology"[\s\S]*?<\/section>/)[0];
  assert.ok(section.includes('5,445-page reference'));
  assert.ok(section.includes('purchase it from Forel'));
  assert.ok(section.includes('I wrote the questions and answers myself.'));
  assert.ok(section.includes('id="catalog"'));
  assert.equal(html.split('5,445-page reference').length-1,1);
  assert.ok(!html.includes('There’s plenty more to test;'));
  assert.ok(!html.includes('id="catalog-title"'));
});
test('car photo appears once alongside the intro with its original caption',()=>{
  const html=fs.readFileSync('site/index.html','utf8');
  const intro=html.match(/<section id="about"[\s\S]*?<\/section>/)[0];
  assert.ok(intro.includes('class="intro-grid"'));
  assert.ok(intro.includes('class="intro-copy"'));
  assert.ok(intro.includes('src="assets/thunderbird-owner.png"'));
  assert.ok(intro.includes('The removal of my eyes was unsolicited.'));
  assert.equal((html.match(/<figure class="owner-photo">/g)||[]).length,1);
  assert.ok(!html.includes('id="the-car"'));
});
test('first release update lists the original ten models below the latest update',()=>{
  const html=fs.readFileSync('site/index.html','utf8');
  assert.ok(html.indexOf('datetime="2026-09-23"')<html.indexOf('datetime="2026-09-08"'));
  assert.ok(html.includes('September 8, 2026</time> — First release'));
  const list=html.match(/<ul class="launch-models">([\s\S]*?)<\/ul>/)[1];
  assert.equal((list.match(/<li>/g)||[]).length,10);
  for(const name of ['GPT-6 Astra','Claude Fable 5.1','GPT-5.6 Sol Pro','Gemini 3.8 Flash','Grok 4.6','Qwen 3.8 Max 0902','GLM 5.3 Flash','Qwen 3.8 Flash','Seed 2.1 Turbo','DeepSeek V4 Vision Exp']) assert.ok(list.includes(`>${name}</a></li>`));
});
test('intro contains the dated bold summary without a pilot label or status dot',()=>{
  const html=fs.readFileSync('site/index.html','utf8');
  assert.ok(!html.includes('id="release"'));
  assert.ok(!html.includes('class="status-dot"'));
  assert.ok(!fs.readFileSync('site/app.js','utf8').includes('$("#release")'));
  assert.ok(html.indexOf('id="tldr"')<html.indexOf('id="benchmark-results"'));
  assert.ok(html.indexOf('id="tldr"')<html.indexOf('id="chart"'));
  assert.ok(html.includes('id="tldr"><strong>GPT-6 Astra'));
  assert.ok(html.indexOf('I built this benchmark')<html.indexOf('id="exported"'));
  const intro=html.match(/<div class="intro-copy">([\s\S]*?)<\/div>/)[1];
  assert.ok(intro.includes('id="exported"'));
  assert.ok(intro.includes('id="tldr"'));
  assert.ok(html.indexOf('id="tldr"')<html.indexOf('id="exported"'));
  assert.match(fs.readFileSync('site/styles.css','utf8'),/\.intro-update\{[^}]*font-style:italic/);
  assert.ok(html.includes('Updated Sept 23, 2026'));
  assert.ok(!html.includes('class="release-stamp"'));
  assert.equal(html.split('GPT-6 Astra has the highest score').length-1,1);
  assert.ok(!html.includes('table-help'));
});
test('dated update introduces three new models without changing the benchmark scope',()=>{
  const html=fs.readFileSync('site/index.html','utf8');
  assert.ok(html.includes('id="updates"'));
  assert.ok(html.includes('<time datetime="2026-09-23">September 23, 2026</time>'));
  assert.ok(html.indexOf('id="updates"')<html.indexOf('id="results"'));
  assert.ok(html.indexOf('id="benchmark-results"')<html.indexOf('id="updates"'));
  assert.ok(html.indexOf('id="updates"')<html.indexOf('id="example"'));
  const rows=JSON.parse(fs.readFileSync('site/data/results.json','utf8')).models;
  assert.equal(rows.length,13);
  for(const model of ['openai/gpt-6-luna','openai/gpt-6-sol','anthropic/claude-opus-5.5']) {
    const row=rows.find(r=>r.model===model);
    assert.ok(row);
    assert.equal(row.questions,119);
    assert.equal(row.exercises,10);
    assert.equal(row.failed_responses,0);
  }
  assert.equal(new Set(rows.map(r=>r.dataset_sha256)).size,1);
  assert.equal(new Set(rows.map(r=>JSON.stringify(r.settings))).size,1);
});
test('both page templates include the supplied Cloudflare beacon exactly once',()=>{
  for (const file of ['site/index.html','site/answer.html']) {
    const html=fs.readFileSync(file,'utf8');
    const scripts=[...html.matchAll(/<script\b[^>]*data-cf-beacon='([^']+)'[^>]*><\/script>/g)];
    assert.equal(scripts.length,1);
    assert.equal(JSON.parse(scripts[0][1]).token,'16ae25d601f6474c958871d21e81d946');
    assert.ok(scripts[0][0].includes('src="https://static.cloudflareinsights.com/beacon.min.js"'));
    assert.ok(scripts[0].index<html.indexOf('</body>'));
  }
});
test('landing page puts Benchmark Results first and removes the stats row',()=>{
  const html=fs.readFileSync('site/index.html','utf8');
  assert.ok(html.includes('<h1 id="title">Part Catalog Bench</h1>'));
  assert.ok(html.includes('Example questions from the benchmark'));
  assert.ok(!html.includes('The questions below are the sort of things I wanted help with.'));
  assert.ok(!html.includes('Results so far'));
  assert.ok(!html.includes('id="scope"'));
  const ids=['n-questions','n-exercises','best-score','n-models'];
  for(const id of ids) {
    assert.ok(!html.includes(`id="${id}"`));
    assert.ok(!fs.readFileSync('site/app.js','utf8').includes(`$("#${id}")`));
  }
  assert.ok(!html.includes('class="stats"'));
  assert.ok(html.includes('<h2 id="chart-title">Benchmark Results</h2>'));
  assert.ok(html.indexOf('id="benchmark-results"')<html.indexOf('id="example"'));
  assert.ok(html.indexOf('id="benchmark-results"')<html.indexOf('id="results"'));
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
test('all update model mentions link to valid models and can open their details',()=>{
  const html=fs.readFileSync('site/index.html','utf8');
  const updates=html.match(/<section id="updates"[\s\S]*?<\/section>/)[0];
  const links=[...updates.matchAll(/href="(#model=[^"]+)"/g)];
  assert.equal(links.length,15);
  for (const [,hash] of links) {
    const model=decodeURIComponent(hash.slice(7));
    const index=rows.findIndex(r=>r.model===model);
    assert.ok(index>=0);
    const toggle=element(`#model-toggle-${index}`);
    let scrolled=false;
    toggle.focus=()=>{};
    toggle.scrollIntoView=()=>{scrolled=true;};
    context.window.matchMedia=()=>({matches:false});
    context.linkHash=hash;
    vm.runInContext('data={models:rows};expandedModels.clear();openModelLink(linkHash)',context);
    assert.ok(vm.runInContext('expandedModels.has(decodeURIComponent(linkHash.slice(7)))',context));
    assert.ok(scrolled);
  }
  assert.doesNotThrow(()=>vm.runInContext('openModelLink("#model=%invalid");openModelLink("#model=missing")',context));
});
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
  assert.ok(element('#leaderboard').innerHTML.includes('openrouter'));
  assert.ok(fs.readFileSync('site/index.html','utf8').includes('These models were accessed through OpenRouter.'));
  assert.ok(element('#leaderboard').innerHTML.includes('Easy'));
  const categories=vm.runInContext('barsMarkup(rows[0],"by_category")',context);
  assert.ok(categories.includes('Part identification'));
  assert.ok(!categories.includes('Quantities'));
});
test('model activation scrolls and focuses details, but initial selection does not',()=>{
  let scrolls=0,focuses=0,behavior;
  for(let i=0;i<rows.length;i++) {
    const detail=element(`#model-toggle-${i}`);
    detail.focus=options=>{assert.equal(options.preventScroll,true);focuses++;};
    detail.scrollIntoView=options=>{assert.equal(options.block,'start');behavior=options.behavior;scrolls++;};
  }
  context.window.matchMedia=()=>({matches:false});
  vm.runInContext('data={models:rows};expandedModels.clear();renderTable();renderChart()',context);
  assert.equal(scrolls,0);
  assert.equal(focuses,0);
  assert.ok(!element('#leaderboard').innerHTML.includes('aria-expanded="true"'));
  vm.runInContext('selectModel(rows[1].model,true)',context);
  assert.equal(scrolls,1);
  assert.equal(focuses,1);
  assert.equal(behavior,'smooth');
  context.window.matchMedia=()=>({matches:true});
  vm.runInContext('selectModel(rows[2].model,true)',context);
  assert.equal(behavior,'instant');
  const script=fs.readFileSync('site/app.js','utf8');
  assert.ok(script.includes('selectModel(g.dataset.point, true)'));
  assert.ok(script.includes('toggleModel(b.dataset.model)'));
});
test('inline disclosures retain independent breakdowns through sorting and reopening',()=>{
  vm.runInContext('expandedModels.clear();selectModel(rows[0].model);selectModel(rows[1].model);breakdowns.set(rows[0].model,"by_category");sortKey="cost_usd";direction=1;renderTable()',context);
  let html=element('#leaderboard').innerHTML;
  assert.equal((html.match(/aria-expanded="true"/g)||[]).length,2);
  assert.ok(html.includes('colspan="6"'));
  assert.ok(html.includes('Part identification'));
  assert.ok(html.includes('Easy'));
  vm.runInContext('toggleModel(rows[0].model)',context);
  assert.equal(vm.runInContext('expandedModels.has(rows[0].model)',context),false);
  vm.runInContext('toggleModel(rows[0].model)',context);
  assert.equal(vm.runInContext('breakdowns.get(rows[0].model)',context),'by_category');
  const page=fs.readFileSync('site/index.html','utf8');
  assert.ok(page.includes('>Detailed Results</h2>'));
  assert.ok(!page.includes('id="model-detail"'));
});
