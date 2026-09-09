"use strict";
const $ = (selector) => document.querySelector(selector);
const labels = {
  "openai/gpt-6-astra": "GPT-6 Astra",
  "anthropic/claude-fable-5.1": "Claude Fable 5.1",
  "openai/gpt-5.6-sol-pro": "GPT-5.6 Sol Pro",
  "google/gemini-3.8-flash": "Gemini 3.8 Flash",
  "deepseek/deepseek-v4-flash-vision-exp": "DeepSeek V4 Vision Exp",
  "x-ai/grok-4.6": "Grok 4.6",
  "qwen/qwen3.8-max-0902": "Qwen 3.8 Max 0902",
  "qwen/qwen3.8-flash": "Qwen 3.8 Flash",
  "z-ai/glm-5.3-flash": "GLM 5.3 Flash",
  "bytedance-seed/seed-2-1-turbo": "Seed 2.1 Turbo",
};
const categoryLabels = {
  assembly_stack_tracing: "Assembly order", catalog_notation: "Catalog notation",
  component_identification: "Part identification", cross_view_matching: "Cross-view matching",
  functional_reasoning: "Part function", quantity_reasoning: "Quantities",
  routed_system_tracing: "Connection tracing", spatial_relationship: "Spatial relationships",
  easy: "Easy", medium: "Medium", hard: "Hard",
};
const name = (r) => labels[r.model] || r.model;
const pct = (v) => v == null ? "—" : `${(v * 100).toFixed(1)}%`;
const money = (v) => v == null ? "Unreported" : `$${v.toFixed(2)}`;
const seconds = (v) => v == null ? "—" : `${v.toFixed(1)} s`;
const esc = (s) => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let data, selected, sortKey = "score", direction = -1;

function frontier(rows) {
  const eligible = rows.filter(r => r.cost_usd != null && r.cost_usd > 0);
  return eligible.filter(r => !eligible.some(other =>
    other.cost_usd <= r.cost_usd && other.score >= r.score &&
    (other.cost_usd < r.cost_usd || other.score > r.score)
  )).sort((a,b) => a.cost_usd - b.cost_usd);
}

function sortedRows(rows, key, dir) {
  return [...rows].sort((a,b) => {
    const av = key === "model" ? name(a) : a[key];
    const bv = key === "model" ? name(b) : b[key];
    if (av == null) return bv == null ? 0 : 1;
    if (bv == null) return -1;
    return (typeof av === "string" ? av.localeCompare(bv) : av - bv) * dir;
  });
}

function renderTable() {
  const efficient = new Set(frontier(data.models).map(r => r.model));
  $("#leaderboard").innerHTML = sortedRows(data.models,sortKey,direction).map(r => `<tr class="${selected === r.model ? "selected" : ""}">
    <td><button class="model-button" data-model="${esc(r.model)}" aria-pressed="${selected === r.model}">${esc(name(r))}</button>${efficient.has(r.model) ? '<span class="frontier-tag">FRONTIER</span>' : ""}</td>
    <td class="score">${pct(r.score)}</td><td>${pct(r.ci95[0])}–${pct(r.ci95[1])}</td>
    <td>${money(r.cost_usd)}</td><td>${seconds(r.median_seconds)}</td><td class="${r.failed_responses ? "failure" : ""}">${r.failed_responses}/${r.questions}<small>${pct(r.failed_responses / r.questions)}</small></td>
  </tr>`).join("");
  document.querySelectorAll(".model-button").forEach(b => b.addEventListener("click", () => selectModel(b.dataset.model)));
}

function renderDetails() {
  const r = data.models.find(m => m.model === selected);
  if (!r) return;
  $("#model-detail").hidden = false;
  $("#detail-title").textContent = name(r);
  $("#model-id").textContent = `${r.model} · ${r.provider}`;
  const key = $("#breakdown").value;
  const groups = Object.entries(r[key]);
  if (key === "by_difficulty") groups.sort((a,b) => ["easy","medium","hard"].indexOf(a[0]) - ["easy","medium","hard"].indexOf(b[0]));
  $("#bars").innerHTML = groups.length ? groups.map(([label,g]) => `<div class="bar-row"><div class="bar-label"><span>${esc(categoryLabels[label] || label)}<small>n = ${g.questions}</small></span><strong>${pct(g.score)}</strong></div><div class="bar-track"><div class="bar-fill" style="width:${Math.max(0,Math.min(100,g.score*100))}%"></div></div></div>`).join("") : '<p class="caption">No breakdowns meet the minimum group size.</p>';
  const metrics = [
    ["Overall score", pct(r.score)], ["Fully correct answers", pct(r.strict_score)],
    ["Score with list partial credit",pct(r.partial_score)], ["Model cost",money(r.cost_usd)],
    ["Rubric grader cost",r.grader_cost_usd == null ? "Unreported" : `$${r.grader_cost_usd.toFixed(4)}`],
    ["95th percentile latency",seconds(r.p95_seconds)], ["Failed responses",`${r.failed_responses} / ${r.questions}`],
    ["Reused / assembled responses",`${r.reused_responses} / ${r.questions}`],
    ["Run assembled",new Date(r.assembled_at).toLocaleDateString(undefined,{year:"numeric",month:"short",day:"numeric",timeZone:"UTC"})],
    ["Reasoning effort",r.settings.reasoning_effort || "Provider default"],
    ["Maximum output tokens",r.settings.max_tokens.toLocaleString()],
  ];
  $("#model-metrics").innerHTML = metrics.map(([k,v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("");
}

function chartMarkup(rows, compact = false) {
  const width = compact ? 440 : 1100, height = compact ? 420 : 470;
  const left = compact ? 50 : 70, right = compact ? 25 : 80, top = 24, bottom = 70;
  const plotWidth = width-left-right, plotHeight = height-top-bottom;
  const eligible = rows.filter(r => Number.isFinite(r.cost_usd) && r.cost_usd > 0);
  if (!eligible.length) return '<p class="caption">The chart needs complete, positive cost data.</p>';
  const lo = Math.floor(Math.log10(Math.min(...eligible.map(r=>r.cost_usd)))*2)/2-.18;
  const hi = Math.ceil(Math.log10(Math.max(...eligible.map(r=>r.cost_usd)))*2)/2+.18;
  const x = cost => left + (Math.log10(cost)-lo)/(hi-lo)*plotWidth;
  const y = score => top + (1-score)*plotHeight;
  const ticks = [];
  for(let power=Math.floor(lo);power<=Math.ceil(hi);power++) for(const m of [1,2,5]) {
    const v = m * 10**power;
    if(Math.log10(v)>=lo && Math.log10(v)<=hi) ticks.push(v);
  }
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="plot-title plot-description"><title id="plot-title">Model score versus candidate cost</title><desc id="plot-description">Higher scores and lower costs are better. Vertical lines show 95 percent confidence intervals. The leaderboard provides the same values as text.</desc><rect width="${width}" height="${height}" fill="white"/><g font-family="Arial, sans-serif" font-size="${compact?12:14}" fill="#536879">`;
  for(let value=0;value<=100;value+=20) svg += `<line x1="${left}" x2="${width-right}" y1="${y(value/100)}" y2="${y(value/100)}" stroke="#e2e9ef"/><text x="${left-12}" y="${y(value/100)+5}" text-anchor="end">${value}%</text>`;
  for(const value of ticks) svg += `<line x1="${x(value)}" x2="${x(value)}" y1="${top}" y2="${height-bottom}" stroke="#edf1f5"/><text x="${x(value)}" y="${height-bottom+26}" text-anchor="middle">$${value < 1 ? value.toFixed(2) : value}</text>`;
  svg += `<text x="${left}" y="14" font-size="12">Score</text><text x="${left+plotWidth/2}" y="${height-12}" text-anchor="middle">Cost for all questions (USD · log scale)</text></g>`;
  const efficient = frontier(rows);
  const efficientIds = new Set(efficient.map(r=>r.model));
  if(efficient.length>1) svg += `<polyline points="${efficient.map(r=>`${x(r.cost_usd)},${y(r.score)}`).join(" ")}" fill="none" stroke="#1558d6" stroke-width="2" stroke-dasharray="6 5"/>`;
  const occupied = [];
  eligible.forEach(r => {
    const cx=x(r.cost_usd), cy=y(r.score), color=efficientIds.has(r.model)?"#1558d6":"#58758e";
    const label=name(r), estimatedWidth=label.length*(compact?6.1:7.3);
    let tx=cx+12, anchor="start", ty=cy-12;
    if(tx+estimatedWidth>width-right+35){tx=cx-12;anchor="end";}
    if(compact && label.length>20){tx=Math.max(left+8,Math.min(width-estimatedWidth-8,cx-60));anchor="start";ty=cy+25;}
    let boxX=anchor==="end"?tx-estimatedWidth:tx;
    for(let attempt=0;attempt<10 && occupied.some(b=>Math.abs(b.y-ty)<19 && boxX<b.x+b.w+6 && boxX+estimatedWidth>b.x-6);attempt++) ty+=19;
    ty=Math.max(18,Math.min(height-bottom-4,ty));occupied.push({x:boxX,y:ty,w:estimatedWidth});
    svg += `<g data-point="${esc(r.model)}" tabindex="0" role="button" aria-label="${esc(name(r))}: ${pct(r.score)}, ${money(r.cost_usd)}. Show details." style="cursor:pointer"><title>${esc(name(r))}: ${pct(r.score)}, ${money(r.cost_usd)}; CI ${pct(r.ci95[0])}–${pct(r.ci95[1])}</title><line x1="${cx}" x2="${cx}" y1="${y(r.ci95[1])}" y2="${y(r.ci95[0])}" stroke="${color}" opacity=".55" stroke-width="2"/><path d="M${cx-5},${y(r.ci95[1])}h10 M${cx-5},${y(r.ci95[0])}h10" fill="none" stroke="${color}"/><circle cx="${cx}" cy="${cy}" r="${r.model===selected?8:6}" fill="${color}" stroke="white" stroke-width="2"/><circle cx="${cx}" cy="${cy}" r="15" fill="transparent"/><text x="${tx}" y="${ty}" text-anchor="${anchor}" font-family="Arial, sans-serif" font-size="${compact?12:14}" font-weight="600" fill="#152637" stroke="white" stroke-width="4" paint-order="stroke">${esc(label)}</text></g>`;
  });
  return svg+"</svg>";
}

function renderChart() {
  $("#chart").innerHTML = chartMarkup(data.models,window.innerWidth<600);
  document.querySelectorAll("[data-point]").forEach(g => {
    const activate = () => selectModel(g.dataset.point);
    g.addEventListener("click",activate);
    g.addEventListener("keydown",e=>{if(e.key==="Enter" || e.key===" "){e.preventDefault();activate();}});
  });
}
function selectModel(model) { selected=model;renderTable();renderDetails();renderChart(); }

async function start() {
  try {
    const response = await fetch("data/results.json",{cache:"no-store"});
    if(!response.ok) throw Error(`Results could not be loaded (${response.status}).`);
    data=await response.json();
    if(data.schema_version!==1 || !Array.isArray(data.models)) throw Error("Unsupported results format.");
    $("#release").textContent=data.release;
    $("#exported").textContent=`Updated ${new Date(data.exported_at).toLocaleString(undefined,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit",timeZoneName:"short"})}`;
    $("#n-models").textContent=data.models.length;
    if(!data.models.length){$("#chart").textContent="No completed evaluations are available yet.";return;}
    const first=data.models[0], settings=first.settings;
    $("#n-questions").textContent=first.questions;
    $("#n-exercises").textContent=first.exercises;
    $("#best-score").textContent=pct(Math.max(...data.models.map(r=>r.score)));
    $("#protocol").textContent=`The output limit is ${settings.max_tokens.toLocaleString()} tokens, with ${settings.reasoning_effort || "the provider’s default"} reasoning and temperature set to ${settings.temperature ?? "the default"}. Requests have a ${settings.timeout_seconds}-second timeout and up to ${settings.retries} retries. Free-text answers use ${settings.grader_model} as the grader, with a ${settings.grader_max_tokens}-token output limit.`;
    selectModel(first.model);
    $("#download-chart").disabled=false;
  } catch(error) {
    $("#load-error").hidden=false;
    $("#load-error").textContent=`${error.message} Reload this page or download the CSV below. For a local preview, serve the site over HTTP.`;
    $("#exported").textContent="Results unavailable";
  }
}
document.querySelectorAll("[data-sort]").forEach(button=>button.addEventListener("click",()=>{
  const key=button.dataset.sort;
  direction=key===sortKey?-direction:(key==="score"?-1:1);sortKey=key;
  document.querySelectorAll("[data-sort]").forEach(b=>{
    b.parentElement.setAttribute("aria-sort",b===button?(direction===1?"ascending":"descending"):"none");
    b.textContent=b.textContent.replace(/[↑↓↕]$/,b===button?(direction===1?"↑":"↓"):"↕");
  });
  if(data) renderTable();
}));
$("#breakdown").addEventListener("change",()=>{if(data)renderDetails();});
$("#download-chart").addEventListener("click",()=>{
  const blob=new Blob([chartMarkup(data.models)],{type:"image/svg+xml;charset=utf-8"});
  const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="part-catalog-bench-pareto.svg";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
let resizeTimer;
async function copyCitation() {
  try {
    await navigator.clipboard.writeText($("#citation-bibtex").textContent.trim());
    $("#citation-status").textContent="Copied.";
  } catch {
    $("#citation-status").textContent="Couldn’t copy automatically. Select the text above or download the .bib file.";
  }
}
$("#copy-citation").hidden=false;
$("#copy-citation").addEventListener("click",copyCitation);
window.addEventListener("resize",()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(data)renderChart();},100);});
start();
