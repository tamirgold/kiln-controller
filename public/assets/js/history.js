(() => {
'use strict';
const $=id=>document.getElementById(id),finite=v=>typeof v==='number'&&Number.isFinite(v),num=(v,d=1)=>finite(v)?v.toLocaleString(undefined,{maximumFractionDigits:d,minimumFractionDigits:d}):'—';
const hm=s=>finite(s)?Math.floor(s/3600)+'h '+String(Math.floor(s/60)%60).padStart(2,'0')+'m':'—';
const date=s=>new Date(s*1000).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'});
let overview=null,detail=null,selected=null,chart=null,loading=false,loadingDetail=false;
let clearing=false,reviewing=false,clearSnapshot=null,viewGeneration=0;
const unit=()=>'°'+(overview&&overview.temp_scale||'c').toUpperCase(),temp=v=>finite(v)?overview.temp_scale==='f'?v*1.8+32:v:null,rate=v=>v*(overview.temp_scale==='f'?1.8:1);
const status=s=>({RUNNING:'In progress',PAUSED:'Paused',completed:'Completed',stopped:'Stopped',interrupted:'Interrupted',sensor_fault:'Sensor fault',over_temperature:'Temperature limit',controller_fault:'Controller fault',replaced:'Replaced'})[s]||s;
function cell(row,text,tag='td'){const td=document.createElement(tag);td.textContent=text;row.append(td);return td;}
function money(v,currency){return finite(v)?(currency||'')+num(v,2):'—';}
async function load(){
 if(loading||clearing)return;loading=true;const generation=viewGeneration;
 try{const r=await fetch('/api/firings',{cache:'no-store'});if(!r.ok)throw new Error('Firing history is unavailable. Reconnecting…');const data=await r.json();if(generation!==viewGeneration)return;overview=data;render();if(selected)await select(selected,false);}
 catch(e){$('history_error').textContent=e.message;$('history_error').hidden=false;}finally{loading=false;}
}
function render(){
 $('clear_history').disabled=clearing||reviewing||!overview.clear||overview.clear.count===0;
 const s=overview.summary,a=s.averages;$('history_error').hidden=!overview.error;$('history_error').textContent=overview.error||'';$('simulation_notice').hidden=!overview.simulate;
 $('finished_count').textContent=s.finished_count;$('finished_note').textContent=s.completed_count+' completed · '+s.active_count+' in progress';
 $('average_duration').textContent=hm(a.elapsed_seconds.value);$('average_energy').textContent=num(a.energy_kwh.value,2);
 $('average_cost').textContent=s.costs.length?s.costs.map(c=>money(c.average,c.currency_type)).join(' / '):'—';
 $('average_note').textContent='Averages across '+s.finished_count+' ended firings, including stopped or interrupted runs. In-progress firings are excluded. Energy and cost use '+a.energy_kwh.count+' available records; partial or estimated totals are marked in each firing.';
 $('record_count').textContent=s.firing_count+' saved';$('firing_rows').replaceChildren();$('empty_history').hidden=!!s.firing_count;
 overview.records.forEach(r=>{
  const tr=document.createElement('tr');if(r.id===selected)tr.className='selected';const name=cell(tr,''),strong=document.createElement('button'),small=document.createElement('small');strong.className='text-button firing-name';strong.textContent=r.profile;strong.onclick=()=>select(r.id,true);small.textContent=date(r.started_at);name.append(strong,small);
  cell(tr,status(r.status));cell(tr,hm(r.stats.elapsed_seconds));cell(tr,num(temp(r.stats.peak_temperature_c))+unit());cell(tr,num(r.stats.energy_kwh,2)+' kWh');cell(tr,money(r.stats.cost,r.stats.currency_type));
  const action=cell(tr,''),button=document.createElement('button');button.className='text-button';button.textContent='View';button.setAttribute('aria-label','View '+r.profile+' '+date(r.started_at));button.onclick=()=>select(r.id,true);action.append(button);$('firing_rows').append(tr);
 });
 $('ramp_rows').replaceChildren();s.ramps.forEach(b=>{const tr=document.createElement('tr');[num(temp(b.from_c),0)+'–'+num(temp(b.to_c),0)+unit(),num(rate(b.max_rate_c_hour),0)+unit()+'/h',num(rate(b.mean_rate_c_hour),0)+unit()+'/h',b.windows,b.firing_count].forEach(v=>cell(tr,v));$('ramp_rows').append(tr);});
 $('ramp_empty').hidden=!!s.ramps.length;$('ramp_power').textContent=num(s.kw_elements,1)+' kW kiln';$('last_updated').textContent='Updated '+new Date().toLocaleTimeString();
}
async function select(identity,scroll){
 if(loadingDetail||clearing)return;loadingDetail=true;const generation=viewGeneration;
 try{const r=await fetch('/api/firings/'+encodeURIComponent(identity),{cache:'no-store'});if(!r.ok)throw new Error('Could not load this firing.');const data=await r.json();if(generation!==viewGeneration)return;detail=data;selected=identity;
  const record=detail.record,s=record.stats;$('firing_detail').hidden=false;$('detail_title').textContent=record.profile;$('detail_subtitle').textContent=date(record.started_at)+' · '+status(record.status);
  $('export_csv').href='/api/firings/'+identity+'?format=csv';$('export_firing').href='/api/firings/'+identity;$('export_firing').download='firing-'+identity+'.json';
  const fields=[['Elapsed time',hm(s.elapsed_seconds)],['Peak temperature',num(temp(s.peak_temperature_c))+unit()],['Energy',num(s.energy_kwh,3)+' kWh'],['Cost',money(s.cost,s.currency_type)],['Heater on-time',hm(s.heater_on_seconds)],['Average temperature',num(temp(s.mean_temperature_c))+unit()],['Average target error',num(finite(s.mean_tracking_error_c)?rate(s.mean_tracking_error_c):null)+unit()],['Catch-up time',hm(s.catchup_seconds)]];
  $('detail_stats').replaceChildren();fields.forEach(([label,value])=>{const group=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;group.append(dt,dd);$('detail_stats').append(group);});
  $('sample_count').textContent=s.sample_count.toLocaleString()+' saved readings';
  $('detail_quality').textContent=(s.partial?'Temperature history contains '+s.gaps+' gaps or begins after the firing started. Gaps are excluded from ramp and temperature averages. ':'Temperature history covers this firing from its start. ')+(record.imported_logs?'Earlier readings were recovered from controller logs. ':'')+(s.energy_incomplete?'Energy and cost are partial. ':s.energy_estimated?'Earlier energy use includes a log-based estimate. ':'')+'Cost: '+num(record.kw_elements,1)+' kW × heater on-hours × '+record.currency_type+num(record.kwh_rate,3)+'/kWh.';
  draw();if(scroll)$('firing_detail').scrollIntoView({behavior:'smooth',block:'start'});
 }catch(e){$('history_error').textContent=e.message;$('history_error').hidden=false;}finally{loadingDetail=false;}
}
function clearError(message){$('history_error').textContent=message;$('history_error').hidden=false;}
$('clear_history').onclick=async()=>{
 if(clearing||reviewing)return;reviewing=true;$('clear_history').disabled=true;$('history_message').hidden=true;
 try{
  const r=await fetch('/api/firings',{cache:'no-store'});if(!r.ok)throw new Error('Cannot load the records to clear. Try again.');
  overview=await r.json();render();if(!overview.clear.count)return;
  clearSnapshot={...overview.clear};
  $('clear_description').textContent='Delete '+clearSnapshot.count+' finished firing'+(clearSnapshot.count===1?'':'s')+'? This includes completed, stopped and interrupted runs.';
  $('clear_preserved').textContent='Saved programs are kept. '+(overview.summary.active_count?overview.summary.active_count+' running or paused firing'+(overview.summary.active_count===1?' is':'s are')+' also kept.':'Any firing that starts while this dialog is open will be kept.');
  $('clear_confirm').textContent='Clear '+clearSnapshot.count+' firing'+(clearSnapshot.count===1?'':'s');
  $('clear_dialog').showModal();$('clear_cancel').focus();
 }catch(e){clearError(e.message);}
 finally{reviewing=false;$('clear_history').disabled=!overview||!overview.clear||overview.clear.count===0;}
};
function cancelClear(){if(clearing)return;clearSnapshot=null;$('clear_dialog').close();}
$('clear_cancel').onclick=$('clear_close').onclick=cancelClear;
$('clear_dialog').addEventListener('cancel',e=>{if(clearing)e.preventDefault();else clearSnapshot=null;});
$('clear_confirm').onclick=async()=>{
 if(clearing||!clearSnapshot)return;const reviewed=clearSnapshot;clearing=true;viewGeneration++;
 $('clear_confirm').disabled=$('clear_cancel').disabled=$('clear_close').disabled=true;render();
 let error=null;
 try{
  const r=await fetch('/api/firings/clear',{method:'POST',headers:{'Content-Type':'application/json','X-Kiln-History':reviewed.token},body:JSON.stringify({revision:reviewed.revision,confirm:'clear_finished_firings'})});
  const data=await r.json().catch(()=>({}));if(!r.ok)throw new Error(data.error||'History could not be cleared. Refresh and try again.');
  overview=data;if(!data.records.some(r=>r.id===selected)){selected=null;detail=null;chart=null;$('firing_detail').hidden=true;$('history_chart').replaceChildren();$('history_tooltip').hidden=true;}
  $('history_message').textContent='Cleared '+data.cleared+' finished firing'+(data.cleared===1?'':'s')+'.';$('history_message').hidden=false;render();
 }catch(e){error=e.message||'Connection lost. Refresh to check which records remain.';}
 finally{
  clearing=false;clearSnapshot=null;$('clear_dialog').close();$('clear_confirm').disabled=$('clear_cancel').disabled=$('clear_close').disabled=false;
  await load();if(overview)render();if(error)clearError(error);
 }
};
function svg(tag,attrs={},text){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!==undefined)e.textContent=text;return e;}
function draw(){
 if(!detail)return;const root=$('history_chart'),w=root.clientWidth,h=root.clientHeight,pad={left:48,right:18,top:24,bottom:32};root.replaceChildren();root.setAttribute('viewBox','0 0 '+w+' '+h);
 const points=detail.samples.filter(p=>p.sensor_ready&&finite(p.temperature_c)).map(p=>({...p,x:p.elapsed_seconds,y:temp(p.temperature_c),target:temp(p.target_c)}));
 const maxX=Math.max(60,detail.record.stats.elapsed_seconds),values=points.flatMap(p=>[p.y,p.target]).filter(finite);let minY=Math.min(0,values.reduce((a,b)=>Math.min(a,b),0)),maxY=Math.max(100,values.reduce((a,b)=>Math.max(a,b),0))*1.05;
 const x=v=>pad.left+v/maxX*(w-pad.left-pad.right),y=v=>h-pad.bottom-(v-minY)/(maxY-minY)*(h-pad.top-pad.bottom);
 root.append(svg('title',{},'Recorded measured and target temperature over elapsed firing time'));
 for(let i=0;i<5;i++){const t=minY+(maxY-minY)*i/4;root.append(svg('line',{x1:pad.left,x2:w-pad.right,y1:y(t),y2:y(t),stroke:'#e9eee7'}),svg('text',{x:pad.left-8,y:y(t)+3,'text-anchor':'end',fill:'#73807a','font-size':10},num(t,0)));}
 const ticks=w<450?3:6;for(let i=0;i<ticks;i++){const t=maxX*i/(ticks-1);root.append(svg('text',{x:x(t),y:h-9,'text-anchor':i===0?'start':i===ticks-1?'end':'middle',fill:'#73807a','font-size':10},hm(t)));}
 root.append(svg('text',{x:8,y:12,fill:'#73807a','font-size':10},unit()));
 // Render every recorded interval; a missing interval starts a new path.
 for(const [key,color,dash] of [['target','#548e7a','5 5'],['y','#d97842','']]){
  let path='';points.forEach((p,i)=>{if(!finite(p[key]))return;const prev=points[i-1],start=!prev||p.timestamp-prev.timestamp>30||p.session!==prev.session;path+=(start?'M':'L')+x(p.x).toFixed(2)+','+y(p[key]).toFixed(2)+' ';});
  if(path)root.append(svg('path',{d:path,fill:'none',stroke:color,'stroke-width':2,'stroke-dasharray':dash,'stroke-linejoin':'round'}));
 }
 if(!points.length)root.append(svg('text',{x:w/2,y:h/2,'text-anchor':'middle',fill:'#73807a'},'No temperature readings available'));
 chart={points,x,y,w,h};$('history_tooltip').hidden=true;
}
function tooltip(index){if(!chart||!chart.points.length)return;index=Math.min(chart.points.length-1,Math.max(0,index));chart.cursor=index;const p=chart.points[index],tip=$('history_tooltip');tip.replaceChildren();
 for(const [text,tag] of [['Elapsed '+hm(p.elapsed_seconds),'strong'],['Measured '+num(p.y)+unit(),'div'],['Target '+num(p.target)+unit(),'div'],['Program '+hm(p.program_seconds),'div']]){const e=document.createElement(tag);e.textContent=text;tip.append(e);}
 tip.hidden=false;tip.style.left=Math.max(4,Math.min(chart.w-tip.offsetWidth-4,chart.x(p.x)+10))+'px';tip.style.top=Math.max(2,Math.min(chart.h-tip.offsetHeight-2,chart.y(p.y)-tip.offsetHeight-10))+'px';
}
$('history_chart').addEventListener('pointermove',e=>{if(!chart||!chart.points.length)return;const rect=e.currentTarget.getBoundingClientRect(),xx=e.clientX-rect.left;let index=0;chart.points.forEach((p,i)=>{if(Math.abs(chart.x(p.x)-xx)<Math.abs(chart.x(chart.points[index].x)-xx))index=i;});tooltip(index);});
$('history_chart').addEventListener('pointerleave',()=>{$('history_tooltip').hidden=true;});
$('history_chart').addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)&&chart){e.preventDefault();tooltip((chart.cursor||0)+(e.key==='ArrowRight'?1:-1));}if(e.key==='Escape')$('history_tooltip').hidden=true;});
new ResizeObserver(draw).observe($('history_chart'));load();setInterval(load,60000);
})();
