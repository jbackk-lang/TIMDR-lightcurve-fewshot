'use strict';
const $=id=>document.getElementById(id), token=document.querySelector('meta[name="local-token"]').content;
const state={text:'',table:null,result:null,refs:[],basePeriod:null,busy:false,samples:[],sample:null};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,n=3)=>v==null?'—':Number(v).toLocaleString('pl-PL',{maximumFractionDigits:n});
const C={blue:'#8babf6',mint:'#86dfc4',pale:'#b8c2d8',amber:'#edc77f',red:'#f49a9d'};
const redraw=new Map();
function alertError(e){$('alert').textContent=e.message||String(e);$('alert').hidden=false;$('alert').scrollIntoView({behavior:'smooth',block:'center'});}
function busy(on,msg='') {state.busy=on;document.querySelectorAll('button,input,select').forEach(el=>el.disabled=on);$('analyze').disabled=on||!state.text;$('period').disabled=on||$('unknown').checked;$('busy').textContent=msg||(on?'Trwa obliczanie…':'Gotowe. Możesz zmienić ustawienia.');}
async function api(path,payload){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Local-Token':token},body:JSON.stringify(payload)});const j=await r.json();if(!r.ok)throw Error(j.error||'Błąd analizy');return j;}
function invalidate(){state.result=null;$('results').hidden=true;}
function option(v,label){const o=document.createElement('option');o.value=v;o.textContent=label;return o;}
function updateFilters(){for(const k of ['band','object']){const i=$('map-'+k).value,sel=$('filter-'+k);sel.replaceChildren(option('','Wybierz / jedyna wartość'));if(i!==''&&state.table){for(const v of state.table.values[i]||[])sel.append(option(v,v));if(sel.options.length===2)sel.selectedIndex=1;}}}
function mappingUI(table){state.table=table;$('mapping-panel').hidden=false;$('import-count').textContent=`· ${table.preview.length} pierwszych wierszy`;
for(const k of ['time','magnitude','error','band','object']){const select=$('map-'+k);select.replaceChildren(option('','Nie podano'));table.headers.forEach((s,i)=>select.append(option(i,s)));select.value=table.suggest[k]??'';}
updateFilters();$('preview').innerHTML='<table><thead><tr>'+table.headers.map(s=>'<th>'+esc(s)+'</th>').join('')+'</tr></thead><tbody>'+table.preview.map(r=>'<tr>'+r.map(s=>'<td>'+esc(s)+'</td>').join('')+'</tr>').join('')+'</tbody></table>';
if(table.suggest.time===null||table.suggest.magnitude===null)$('mapping-panel').open=true;
}
function payload(){return {text:state.text,mapping:Object.fromEntries(['time','magnitude','error','band','object'].map(k=>[k,$('map-'+k).value])),time_unit:$('time-unit').value,band:$('filter-band').value,object:$('filter-object').value,declared_band:$('declared-band').value,allow_experimental:$('experimental').checked,period:$('unknown').checked?null:($('period').value||null)};}
async function loadFile(file){if(!file||state.busy)return;invalidate();state.text='';state.sample=null;$('example-note').hidden=true;$('download-example').hidden=true;$('alert').hidden=true;busy(true,'Odczytuję kolumny…');try{if(file.size>5_000_000)throw Error('Plik przekracza 5 MB. Wybierz jeden obiekt i jedno pasmo.');const text=await file.text();const table=await api('/api/inspect',{text});state.text=text;mappingUI(table);$('filename').textContent=file.name;state.basePeriod=null;$('time-unit').value='days';$('period-results').replaceChildren();$('periodogram').hidden=true;}catch(e){alertError(e);}finally{busy(false,'Sprawdź kolumny, jednostkę czasu i okres, następnie uruchom analizę.');}}
async function run(){if(!state.text||state.busy)return;$('alert').hidden=true;invalidate();busy(true,'Sprawdzam jakość, fazę i spójność harmonicznych…');try{const p=payload();const result=await api('/api/analyze',p);if(state.basePeriod===null&&result.period)state.basePeriod=result.period;state.result=result;render(result);$('results').scrollIntoView({behavior:'smooth',block:'start'});}catch(e){alertError(e);}finally{busy(false);}}

// Canvas charts are rendered locally; no measurements are sent to a plotting service.
function plot(id,series,{xlabel='',ylabel='',invert=false,bars=false,xlim=null,ylim=null}={}){
const canvas=$(id);if(!canvas)return;
const paint=()=>{const w=canvas.clientWidth;if(!w)return;const h=Number(canvas.dataset.logicalHeight||canvas.getAttribute('height'))||260;canvas.dataset.logicalHeight=h;const dpr=window.devicePixelRatio||1;canvas.style.height=h+'px';canvas.width=w*dpr;canvas.height=h*dpr;const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
const area={left:57,top:18,right:w-16,bottom:h-40};const pts=series.flatMap(s=>s.x.map((x,i)=>[x,s.y[i]])).filter(p=>p.every(Number.isFinite));if(!pts.length){ctx.fillStyle=C.pale;ctx.fillText('Brak danych do wykresu',20,60);return;}
let xmin=xlim?xlim[0]:Math.min(...pts.map(p=>p[0])),xmax=xlim?xlim[1]:Math.max(...pts.map(p=>p[0]));let ymin=ylim?ylim[0]:Math.min(...pts.map(p=>p[1])),ymax=ylim?ylim[1]:Math.max(...pts.map(p=>p[1]));if(bars)ymin=0;if(xmin===xmax)xmax=xmin+1;if(ymin===ymax){ymin-=.1;ymax+=.1;}if(!ylim){const pad=(ymax-ymin)*.08;ymax+=pad;if(!bars)ymin-=pad;}
const X=x=>area.left+(x-xmin)/(xmax-xmin)*(area.right-area.left),Y=y=>invert?area.top+(y-ymin)/(ymax-ymin)*(area.bottom-area.top):area.bottom-(y-ymin)/(ymax-ymin)*(area.bottom-area.top);
ctx.font='10px system-ui';ctx.lineWidth=1;
for(let i=0;i<=4;i++){const x=xmin+(xmax-xmin)*i/4,y=ymin+(ymax-ymin)*i/4;ctx.strokeStyle='#26364b';ctx.beginPath();ctx.moveTo(area.left,Y(y));ctx.lineTo(area.right,Y(y));ctx.stroke();ctx.fillStyle='#9cabbe';ctx.textAlign='right';ctx.fillText(fmt(y,3),area.left-7,Y(y)+3);ctx.textAlign='center';ctx.fillText(fmt(x,2),X(x),area.bottom+18);}
ctx.fillStyle='#9cabbe';ctx.textAlign='center';ctx.fillText(xlabel,(area.left+area.right)/2,h-5);ctx.save();ctx.translate(12,(area.top+area.bottom)/2);ctx.rotate(-Math.PI/2);ctx.fillText(ylabel,0,0);ctx.restore();
ctx.save();ctx.beginPath();ctx.rect(area.left,area.top,area.right-area.left,area.bottom-area.top);ctx.clip();series.forEach((s,si)=>{ctx.strokeStyle=s.color||C.blue;ctx.fillStyle=s.color||C.blue;ctx.lineWidth=s.width||1.7;ctx.globalAlpha=s.alpha??1;
if(bars){const bw=(area.right-area.left)/Math.max(s.x.length,1)*.64/series.length;s.x.forEach((x,i)=>{const base=X(x)+(si-(series.length-1)/2)*bw;ctx.fillRect(base-bw/2,Math.min(Y(s.y[i]),Y(0)),bw-1,Math.abs(Y(s.y[i])-Y(0)));});}
else if(s.scatter){s.x.forEach((x,i)=>{if(s.errors?.[i]!=null){ctx.globalAlpha=.2;ctx.beginPath();ctx.moveTo(X(x),Y(s.y[i]-s.errors[i]));ctx.lineTo(X(x),Y(s.y[i]+s.errors[i]));ctx.stroke();ctx.globalAlpha=s.alpha??.6;}ctx.beginPath();ctx.arc(X(x),Y(s.y[i]),s.radius||2,0,Math.PI*2);ctx.fill();});}
else{ctx.beginPath();s.x.forEach((x,i)=>{if(i===0)ctx.moveTo(X(x),Y(s.y[i]));else ctx.lineTo(X(x),Y(s.y[i]));});ctx.stroke();}});ctx.restore();ctx.globalAlpha=1;
canvas.onmousemove=e=>{const r=canvas.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;let best=null,dist=Infinity;for(const s of series)s.x.forEach((x,i)=>{const d=(X(x)-mx)**2+(Y(s.y[i])-my)**2;if(d<dist){dist=d;best=[x,s.y[i]];}});canvas.title=best?`${xlabel}: ${fmt(best[0],6)} · ${ylabel}: ${fmt(best[1],5)}`:'';};
};redraw.set(id,paint);paint();}

function render(r){$('results').hidden=false;const q=r.quality,s=r.signal;
$('quality-status').textContent=q.ready?'Formalne minimum spełnione. Przeczytaj uwagi przed interpretacją.':'Najpierw diagnostyka — klasyfikacja została wstrzymana.';
$('quality-badge').textContent=q.ready?(q.warnings.length?'Z UWAGAMI':'MINIMUM SPEŁNIONE'):'DO POPRAWY';$('quality-badge').className='badge'+(!q.ready||q.warnings.length?' warn':'');
const occupied=s?s.counts.filter(v=>v>0).length:null;
$('metrics').innerHTML=[[r.stats.usable_points,'różnych chwil pomiaru'],[occupied==null?'—':`${occupied}/32`,'przedziałów fazy'],[fmt(r.metrics.span_days,2)+' d','rozpiętość obserwacji'],[fmt(r.metrics.median_error,4)+' mag','mediana błędu']].map(([v,t])=>`<div class="metric"><strong>${esc(v)}</strong><span>${esc(t)}</span></div>`).join('');
$('quality-messages').innerHTML=q.blockers.map(x=>`<div class="notice bad">${esc(x)}</div>`).join('')+q.warnings.map(x=>`<div class="notice">${esc(x)}</div>`).join('');
const t0=r.raw.time[0];plot('raw-chart',[{x:r.raw.time.map(t=>t-t0),y:r.raw.magnitude,errors:r.raw.error,scatter:true,alpha:.75}],{xlabel:`Dni od ${fmt(t0,5)}`,ylabel:'Magnitudo',invert:true});
const errs=r.error_values,hi=errs.length?Math.max(...errs):1;const hist=Array(16).fill(0);errs.forEach(v=>hist[Math.min(15,Math.floor(v/(hi||1)*16))]++);
plot('error-chart',errs.length?[{x:hist.map((_,i)=>(i+.5)*(hi||1)/16),y:hist,color:C.mint}]:[],{xlabel:'Błąd magnitudo',ylabel:'Liczba punktów',bars:true,xlim:[0,hi||1]});
$('coverage-box').hidden=!s;if(s){$('coverage-count').textContent=`· ${occupied}/32`;$('coverage').innerHTML=s.counts.map((v,i)=>`<div class="${v?'':'empty'}" title="Faza ${fmt(i/32,3)}–${fmt((i+1)/32,3)}: ${v} punktów" aria-label="Przedział ${i+1}: ${v} punktów"></div>`).join('');}
$('import-report').innerHTML=`<p class="hint">Wiersze wejściowe: ${r.stats.input_rows}; odfiltrowane pasma/obiekty: ${r.stats.filtered_rows}; błędny czas: ${r.stats.bad_time}; błędne magnitudo: ${r.stats.bad_magnitude}; granice jasności: ${r.stats.limits}; błędne/brakujące niepewności: ${r.stats.bad_error}; powtórzenia czasu: ${r.stats.duplicates}. Pokazano ${r.raw.displayed}/${r.raw.total} punktów; obliczenia wykorzystują wszystkie poprawne punkty.</p>`+(r.gaps.length?'<table><tr><th>Początek</th><th>Koniec</th><th>Przerwa (dni)</th></tr>'+r.gaps.map(g=>`<tr><td>${fmt(g.start,5)}</td><td>${fmt(g.end,5)}</td><td>${fmt(g.days,3)}</td></tr>`).join('')+'</table>':'<p>Nie wykryto przerw według progu 5× mediana odstępu.</p>');
$('signal-panel').hidden=!s;$('period-diagnostic').hidden=!s;$('comparison-panel').hidden=!s;
if(s){plot('phase-chart',[{x:s.phase,y:r.raw.magnitude,scatter:true,color:C.blue,alpha:.45},{x:s.grid,y:s.raw.map(y=>y*s.amplitude+s.baseline),color:C.pale},{x:s.grid,y:s.filtered.map(y=>y*s.amplitude+s.baseline),color:C.mint,width:2.5}],{xlabel:'Faza',ylabel:'Magnitudo',invert:true,xlim:[0,1]});
plot('harmonic-chart',[{x:[1,2,3,4,5,6,7,8],y:s.harmonic_amplitude,color:C.pale},{x:[1,2,3,4,5,6,7,8],y:s.harmonic_after,color:C.mint}],{xlabel:'Numer harmonicznej',ylabel:'Amplituda (mag)',bars:true,xlim:[.5,8.5]});
$('sieve-facts').innerHTML=`<div class="fact"><strong>${fmt(s.attenuated_energy_pct,1)}% energii harmonicznych osłabione</strong><br>Sito tłumi składowe, nie usuwa pomiarów.</div><div class="fact"><strong>${fmt(s.cycles,1)} cykli w obserwacjach</strong><br>Zgodność jest porównywana między czterema grupami czasu.</div><div class="fact"><strong>Stabilność harmonicznych</strong><br>${s.coherence.map((c,i)=>`H${i+1}: ${fmt(c,2)}`).join(' · ')}</div>`;
let cells='<span>Fragment</span>'+[1,2,3,4,5,6,7,8].map(i=>`<span>H${i}</span>`).join('');s.segment_agreement.forEach((row,i)=>{cells+=`<span>${i+1} / 4</span>`+row.map(v=>`<span class="cell" style="background:${v>=.8?C.mint:v>=.5?C.amber:C.red}" title="Zgodność fazy: ${fmt(v,3)}">${fmt(v,2)}</span>`).join('');});$('stability').innerHTML=cells;
plot('segments-chart',s.segment_templates.map((ys,i)=>({x:s.grid,y:ys,color:[C.blue,C.mint,C.amber,C.red][i]})),{xlabel:'Faza · fragmenty 1 niebieski, 2 zielony, 3 żółty, 4 czerwony',ylabel:'Jasność znormalizowana',invert:true,xlim:[0,1]});
$('period-status').textContent=`Ocena: ${r.period_info.status}. Okres ${fmt(r.period,8)} dnia. To heurystyka zgodności, nie certyfikat okresu.`;
$('sensitivity').innerHTML='<table><tr><th>Wariant</th><th>Okres (dni)</th><th>Reszta / amplituda ↓</th><th>Spójność H1 ↑</th></tr>'+r.period_info.sensitivity.map(v=>`<tr><td>${v.factor===1?'Podany okres':v.factor<1?'−1%':'+1%'}</td><td>${fmt(v.period,8)}</td><td>${fmt(v.residual,4)}</td><td>${fmt(v.coherence,3)}</td></tr>`).join('')+'</table>';
renderComparisons(r);}
const descriptions={'RRab':'RR Lyrae · pulsacja w modzie podstawowym','RRc':'RR Lyrae · pulsacja w pierwszym nadtonie','CEP-F':'Cefeida klasyczna · mod podstawowy','CEP-1O':'Cefeida klasyczna · pierwszy nadton'};
if(r.classification){$('classification').innerHTML='<div class="result-grid">'+Object.entries(r.classification).map(([arm,v])=>`<div class="prediction"><span>${arm==='timdr_lda'?'TIMDR + prosty klasyfikator':'Klasyczny model porównawczy'} · kandydat</span><strong>${esc(v.label)}</strong><p>${esc(descriptions[v.label])}</p>`+Object.entries(v.scores).map(([k,score])=>`<div class="score-row"><span>${esc(k)}</span><div class="score-track"><div class="score-fill" style="width:${score*100}%"></div></div><small>${fmt(score,3)}</small></div>`).join('')+'<p class="hint">Względne wyniki modelu, nie pewność.</p></div>').join('')+'</div>';}else $('classification').innerHTML='<div class="notice bad">Brak klasyfikacji. Najpierw popraw warunki wskazane w panelu jakości. Dostępne wykresy pomagają zrozumieć dane.</div>';
$('explanation').innerHTML=r.explanations.map(t=>`<div class="fact">${esc(t)}</div>`).join('');
$('tips').innerHTML=(q.tips.length?q.tips:['Formalne minimum spełnione. Zbierz niezależne obserwacje w kolejnych cyklach i sprawdź, czy kształt się powtarza.']).map(t=>`<div class="tip">${esc(t)}</div>`).join('');
}
function renderComparisons(r){const s=r.signal;$('comparisons').innerHTML=state.refs.map((ref,i)=>`<div class="compare"><h3>${esc(ref.label)}</h3><p>${esc(ref.id)} · okres ${fmt(ref.period,7)} d</p><div class="legend"><span class="dot blue">Twoja krzywa (dopasowanie)</span><span class="dot mint">OGLE</span></div><canvas id="compare-${i}" height="220" aria-label="Porównanie z ${esc(ref.label)}"></canvas><p>Źródło: <a href="${esc(ref.source)}" target="_blank" rel="noreferrer">OGLE, pasmo I</a></p></div>`).join('');state.refs.forEach((ref,i)=>plot('compare-'+i,[{x:s.grid,y:s.raw,color:C.blue},{x:ref.grid,y:ref.template,color:C.mint}],{xlabel:'Faza',ylabel:'Znormalizowane magnitudo',invert:true,xlim:[0,1]}));}

$('file').addEventListener('change',e=>loadFile(e.target.files[0]));$('drop').addEventListener('dragover',e=>{e.preventDefault();$('drop').classList.add('drag');});$('drop').addEventListener('dragleave',()=>$('drop').classList.remove('drag'));$('drop').addEventListener('drop',e=>{e.preventDefault();$('drop').classList.remove('drag');loadFile(e.dataTransfer.files[0]);});$('analyze').onclick=run;
async function loadSample(key){
if(state.busy)return;
const sample=state.samples.find(s=>s.key===key);
if(!sample){alertError(Error('Przykłady jeszcze się wczytują. Spróbuj ponownie.'));return;}
await loadFile(new File([sample.text],sample.filename,{type:'text/csv'}));if(!state.text)return;
state.sample=sample;$('period').value=sample.period??'';$('unknown').checked=sample.period===null;
$('search-box').hidden=sample.period!==null;$('period').disabled=sample.period===null;
$('declared-band').value='I';$('experimental').checked=false;state.basePeriod=sample.period;
$('pmin').value=sample.pmin;$('pmax').value=sample.pmax;
$('example-note').textContent=sample.description+' '+sample.expected;$('example-note').hidden=false;$('download-example').hidden=false;
if(sample.period!==null)await run();else $('search-box').scrollIntoView({behavior:'smooth',block:'center'});
}
document.querySelectorAll('[data-example]').forEach(b=>b.onclick=()=>loadSample(b.dataset.example));
document.querySelectorAll('[data-tutorial]').forEach(b=>b.onclick=()=>loadSample(b.dataset.tutorial));
$('download-example').onclick=()=>{if(!state.sample)return;const url=URL.createObjectURL(new Blob([state.sample.text],{type:'text/csv'})),a=document.createElement('a');a.href=url;a.download=state.sample.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
document.querySelectorAll('#mapping-panel select,#period,#declared-band,#experimental').forEach(el=>el.addEventListener('change',()=>{invalidate();if(el.id==='map-band'||el.id==='map-object')updateFilters();if(el.id==='period')state.basePeriod=null;}));
$('unknown').addEventListener('change',()=>{invalidate();$('search-box').hidden=!$('unknown').checked;$('period').disabled=$('unknown').checked;});
$('search-period').onclick=async()=>{if(state.busy)return;if(!state.text){alertError(Error('Najpierw wgraj pomiary.'));return;}busy(true,'Szukam okresów — to może potrwać kilkanaście sekund…');$('alert').hidden=true;try{const r=await api('/api/period',{...payload(),pmin:$('pmin').value,pmax:$('pmax').value});$('period-results').innerHTML=`<p class="notice">${esc(r.note)}</p><p class="hint">Siatka: ${r.grid_points} częstotliwości. ${r.fap==null?'Nie wyznaczono FAP.':`FAP dla najsilniejszego piku: ${r.fap.toExponential(2)} (nie pewność okresu).`}</p><div class="actions">`+r.candidates.map(c=>`<button class="secondary candidate" data-period="${c.period}">Sprawdź ${fmt(c.period,7)} d</button>`).join('')+'</div>';$('periodogram').hidden=false;plot('periodogram',[{x:r.frequency,y:r.power,color:C.mint}],{xlabel:'Częstotliwość (1/dzień)',ylabel:'Moc Lomb–Scargle'});document.querySelectorAll('.candidate').forEach(b=>b.onclick=()=>{$('period').value=b.dataset.period;$('unknown').checked=false;$('period').disabled=false;state.basePeriod=Number(b.dataset.period);run();});}catch(e){alertError(e);}finally{busy(false);}};
document.querySelectorAll('[data-shift]').forEach(b=>b.onclick=()=>{if(!state.result?.period)return;$('period').value=state.result.period*Number(b.dataset.shift);run();});$('restore-period').onclick=()=>{if(state.basePeriod){$('period').value=state.basePeriod;run();}};
$('download-report').onclick=()=>{if(!state.result)return;const report={...state.result,report_version:1,created_at:new Date().toISOString(),interpretation:'Diagnostyka heurystyczna; wyniki klasyfikatora nieskalibrowane. Model zamknięty, cztery klasy OGLE I.'};const blob=new Blob([JSON.stringify(report,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='TIMDR-raport-krzywej.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>redraw.forEach(p=>p()),120);});
fetch('/api/references').then(r=>{if(!r.ok)throw Error('Nie można odczytać przykładów OGLE.');return r.json();}).then(r=>state.refs=r).catch(alertError);

fetch('/api/examples').then(r=>{if(!r.ok)throw Error('Nie można odczytać przykładów edukacyjnych.');return r.json();}).then(r=>state.samples=r).catch(alertError);


(async()=>{
const saved=sessionStorage.getItem('timdr-image-curve');if(!saved)return;sessionStorage.removeItem('timdr-image-curve');
try{const d=JSON.parse(saved);await loadFile(new File([d.text],'krzywa-ze-zdjec.csv',{type:'text/csv'}));if(!state.text)return;
$('period').value=d.period??'';$('unknown').checked=!d.period;$('period').disabled=!d.period;$('search-box').hidden=!!d.period;state.basePeriod=d.period;
$('declared-band').value=['I','V'].includes(d.band)?d.band:'unknown';$('experimental').checked=!!d.example;
$('example-note').textContent=d.example?'Krzywa z SYMULOWANYCH zdjęć. Okres zadany: 0,56 dnia. Klasyfikacja jest demonstracją działania, nie identyfikacją prawdziwej gwiazdy. Dla stałej gwiazdy oczekuj komunikatu o słabym sygnale.':'Krzywa z Twoich zdjęć. Sprawdź pasmo i wyznacz okres przed klasyfikacją.';$('example-note').hidden=false;
await run();}catch(e){alertError(e);}
})();
