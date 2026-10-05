(() => {
'use strict';
const $=id=>document.getElementById(id), finite=v=>typeof v==='number'&&Number.isFinite(v), clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const active=s=>s&&['RUNNING','PAUSED'].includes(s.state);
const S={live:null,config:{},profiles:[],runProfile:null,history:[],historyOrigin:null,historyOriginKnown:true,programStart:null,showSkipped:false,zoom:null,lastStatus:0,sockets:{},ready:{},retries:{},mode:'comparison',selected:'',runKey:null,pendingState:null,pendingStorage:null,editorProfile:null,dirty:false,chart:null,confirm:null};
let drawPending=false,toastTimer,commandTimer,storageTimer,chartDrag=null;
let firingOverview=null,historyLoading=null,loadedFiring=null;
const hoursMinutes=s=>Math.floor(Math.max(0,s)/3600)+'h '+String(Math.floor(Math.max(0,s)/60)%60).padStart(2,'0')+'m';
const num=(v,d=1)=>finite(v)?v.toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
const unit=()=>'°'+(S.config.temp_scale||'c').toUpperCase();
const timeFactor=scale=>({s:1,m:60,h:3600}[scale]||60);
const timeWord=scale=>({s:'seconds',m:'minutes',h:'hours'}[scale]||'minutes');
const rateText=rate=>num(rate*timeFactor(S.config.time_scale_slope||'h')/3600,(S.config.time_scale_slope||'h')==='h'?0:2)+unit()+'/'+(S.config.time_scale_slope||'h');
function duration(seconds){seconds=Math.max(0,Math.floor(Number(seconds)||0));return [Math.floor(seconds/3600),Math.floor(seconds/60)%60,seconds%60].map(v=>String(v).padStart(2,'0')).join(':');}
function axisTime(s,signed=false,precise=false){
 const seconds=Math.round(Math.abs(s)),m=Math.round(Math.abs(s)/60),prefix=(precise?seconds:m)?(s<0?'−':signed?'+':''):'';
 if(precise){const h=Math.floor(seconds/3600),minutes=Math.floor(seconds/60)%60;return prefix+(h?h+'h ':'')+(minutes||h?minutes+'m ':'')+(seconds%60)+'s';}
 return prefix+(m>=60?Math.floor(m/60)+'h'+(m%60?' '+m%60+'m':''):m+'m');
}
const signedTime=s=>(Math.abs(s)<1?'':s<0?'−':'+')+hoursMinutes(Math.abs(s));
function validProfile(p){return p&&typeof p.name==='string'&&Array.isArray(p.data)&&p.data.length>=2&&p.data.every((v,i)=>Array.isArray(v)&&finite(v[0])&&finite(v[1])&&v[0]>=0&&(!i||v[0]>p.data[i-1][0]));}
function selected(){return S.profiles.find(p=>p.name===S.selected)||null;}
function chartProfile(){return active(S.live)?(S.runProfile&&S.runProfile.name===S.live.profile?S.runProfile:S.profiles.find(p=>p.name===S.live.profile))||null:selected();}
function fresh(){return !!S.live&&performance.now()-S.lastStatus<10000;}
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>{$('toast').hidden=true;},6000);}
function buttons(){
 const good=fresh(),busy=!!S.pendingState;
 $('stop_button').disabled=!good||!active(S.live)||busy;
 $('start_button').disabled=!good||active(S.live)||S.live.sensor_ready===false||!selected()||busy;
 $('new_button').disabled=!S.ready.storage||!!S.pendingStorage;
 $('edit_button').disabled=!selected()||!S.ready.storage||!!S.pendingStorage;
 $('profile_select').disabled=!S.profiles.length;$('schedule_button').disabled=!selected();$('export_button').disabled=!S.history.length;
 $('save_button').disabled=!S.ready.storage||!!S.pendingStorage;
 $('delete_button').disabled=!S.ready.storage||!!S.pendingStorage||(S.editorProfile&&active(S.live)&&S.editorProfile.name===S.live.profile);
}
function connection(){
 const good=fresh();$('connection').classList.toggle('online',good);
 $('connection_label').textContent=good?'Connected':S.live?'Reconnecting':'Connecting';
 $('connection_notice').hidden=good||(!S.live&&performance.now()<10000);
 document.body.classList.toggle('offline',!good);
 if(!good)$('state_badge').textContent=S.live?'Connection lost':'Connecting';
 buttons();
}
function connect(channel){
 const ws=new WebSocket((location.protocol==='https:'?'wss:':'ws:')+'//'+location.host+'/'+channel);S.sockets[channel]=ws;
 ws.onopen=()=>{S.ready[channel]=true;S.retries[channel]=0;if(channel!=='status')ws.send('GET');else{loadedFiring=null;loadFiringHistory();}buttons();};
 ws.onmessage=e=>{let d;try{d=JSON.parse(e.data);}catch(_){return;}if(channel==='status')status(d);else if(channel==='config'){S.config=d;renderConfig();profileSummary();renderLive();}else storage(d);};
 ws.onerror=()=>ws.close();
 ws.onclose=()=>{S.ready[channel]=false;if(channel==='storage'&&S.pendingStorage){clearTimeout(storageTimer);S.pendingStorage=null;editorError('Connection lost. Check the program list after reconnecting before saving again.');}connection();S.retries[channel]=(S.retries[channel]||0)+1;setTimeout(()=>connect(channel),Math.min(10000,750*Math.pow(1.6,S.retries[channel])));};
}
function rememberProgramStart(d){
 // The controller force-saves the chosen program position at firing start.
 // Later runtime/temperature cannot recover this offset after waits or restarts.
 if(d.source==='controller_log'||!finite(d.run_started_at)||!finite(d.timestamp)||!finite(d.runtime)||d.runtime<0||!finite(d.elapsed_seconds)||d.elapsed_seconds<0||d.elapsed_seconds>1)return;
 if(!S.programStart||S.programStart.origin!==d.run_started_at||d.timestamp<S.programStart.timestamp)S.programStart={origin:d.run_started_at,seconds:d.runtime,timestamp:d.timestamp,temperature:d.sensor_ready!==false&&finite(d.temperature)?d.temperature:null};
}
function addHistory(d){
 rememberProgramStart(d);
 const stamp=finite(d.timestamp)?d.timestamp:d.pidstats&&finite(d.pidstats.time)?d.pidstats.time:null;
 if(!finite(stamp)||!finite(d.temperature)||d.sensor_ready===false)return;
 const last=S.history[S.history.length-1];if(last&&stamp<=last.timestamp)return;
 S.history.push({timestamp:stamp,runtime:d.runtime||0,temperature:d.temperature,target:finite(d.target)?d.target:null,elapsed:finite(d.elapsed_seconds)?d.elapsed_seconds:null});
 if(S.history.length>4000)S.history=S.history.filter((_,i)=>i%2===0||i===S.history.length-1);
}
function status(d){
 if(d.type==='backlog'){
  if(validProfile(d.profile))S.runProfile=d.profile;S.history=[];
  if(Array.isArray(d.log)){d.log.forEach(addHistory);const last=d.log[d.log.length-1];if(last){S.historyOrigin=finite(last.run_started_at)?last.run_started_at:null;S.historyOriginKnown=last.elapsed_origin_known===true;}}
  queueDraw();return;
 }
 if(!['IDLE','RUNNING','PAUSED'].includes(d.state))return;
 const key=active(d)?d.profile+':'+(d.run_started_at||''):null;
 if(key&&S.runKey!==key&&S.live){
  S.showSkipped=false;resetChartZoom();
  const matchingBacklog=S.historyOrigin===d.run_started_at&&S.runProfile&&S.runProfile.name===d.profile;
  if(!matchingBacklog){S.history=[];S.runProfile=null;S.historyOrigin=null;S.historyOriginKnown=true;}
  if(S.programStart&&S.programStart.origin!==d.run_started_at)S.programStart=null;
 }
 if(key){S.runKey=key;S.historyOrigin=finite(d.run_started_at)?d.run_started_at:null;S.historyOriginKnown=d.elapsed_origin_known!==false;}
 if(active(d))addHistory(d);
 if(validProfile(d.profile_data))S.runProfile=d.profile_data;
 S.live=d;S.lastStatus=performance.now();
 if(S.pendingState&&d.state===S.pendingState){clearTimeout(commandTimer);S.pendingState=null;}
 if(!S.selected&&d.profile&&S.profiles.some(p=>p.name===d.profile)){S.selected=d.profile;$('profile_select').value=d.profile;profileSummary();}
 renderLive();connection();queueDraw();loadFiringHistory();
}
function renderConfig(){
 document.querySelectorAll('.temp-unit').forEach(e=>{e.textContent=unit();});$('editor_temp_heading').textContent='Target '+unit();
 $('editor_time_heading').textContent=timeWord(S.config.time_scale_profile)+' from start';$('editor_time_help').textContent='Set cumulative time in '+timeWord(S.config.time_scale_profile)+'. Equal temperatures create a hold.';$('editor_rate_heading').textContent='Rate / '+(S.config.time_scale_slope||'h');
 $('rated_power').textContent=num(S.config.kw_elements,1)+' kW';
 $('tariff').textContent=finite(S.config.kwh_rate)?(S.config.currency_type||'')+num(S.config.kwh_rate,3)+' / kWh':'—';
 $('recovery').textContent=S.config.automatic_restarts===false?'Manual restart':finite(S.config.automatic_restart_window)?'Within '+S.config.automatic_restart_window+' minutes':'—';
 $('limit').textContent=num(S.config.emergency_shutoff_temp,0)+unit();
}
function renderLive(){
 const d=S.live;if(!d)return;$('history_notice').hidden=!d.history_error;$('history_notice').textContent=d.history_error||'';const running=active(d),ready=d.sensor_ready!==false,delta=d.temperature-d.target;
 renderCost();
 $('temperature').textContent=ready?num(d.temperature):'—';$('target').textContent=running?num(d.target):'—';
 $('sensor_notice').hidden=ready;$('simulation_notice').hidden=!d.simulate;$('sensor_dot').classList.toggle('ready',ready);
 $('sensor_status').textContent=ready?'Connected':'Not ready';$('sensor_caption').textContent=d.simulate?'SIMULATED':'MAX31855';
 $('temperature_delta').textContent=!ready?'Sensor needs attention':!running?'Monitoring temperature':Math.abs(delta)<.1?'At target temperature':num(Math.abs(delta))+unit()+(delta<0?' below target':' above target');
 $('state_badge').textContent=d.state==='PAUSED'?'Paused · holding':d.catching_up&&running?'Catching up':running?'Firing in progress':'Ready';
 $('state_badge').className='state-pill'+(running?d.catching_up||d.state==='PAUSED'?' waiting':' running':'');
 $('run_subtitle').textContent=running?d.profile+' · '+(d.simulate?'Simulation':'Live kiln readings'):'Your kiln is idle. Choose a program when you’re ready.';
 $('active_profile').textContent=running?d.profile:'No active program';document.querySelector('.run-card').classList.toggle('catching',!!d.catching_up&&running);
 const output=running&&ready&&d.pidstats&&finite(d.pidstats.out)?clamp(d.pidstats.out,0,1):running?null:0;
 $('output').textContent=output===null?'—':num(output*100,0);$('power_fill').style.width=(output||0)*100+'%';
 $('power_note').textContent=finite(S.config.kw_elements)&&output!==null?'≈ '+num(S.config.kw_elements*output)+' kW of '+num(S.config.kw_elements,0)+' kW · requested':'Duty cycle requested by PID';
 let next=null,prev=null;const p=chartProfile();if(p&&running){const i=p.data.findIndex(v=>v[0]>d.runtime);if(i>0){prev=p.data[i-1];next=p.data[i];}}
 const phase=next?next[1]>prev[1]?'Ramping up':next[1]<prev[1]?'Cooling segment':'Holding temperature':running?'Program running':'Ready when you are';
 $('target_note').textContent=running?phase:'No active program';$('phase_label').textContent=d.catching_up&&running?'WAITING FOR TEMPERATURE':phase;
 $('phase_detail').textContent=next?(next[1]===prev[1]?'Hold at ':next[1]>prev[1]?'Ramp toward ':'Cool toward ')+num(next[1],0)+unit():running?'Following the selected schedule':'Choose a program below';
 $('progress_note').textContent=d.state==='PAUSED'?'Paused: the controller maintains temperature. Elapsed firing time continues counting.':d.catching_up&&running?'Program progress waits while the kiln catches up. Elapsed firing time keeps counting.':'Program time left excludes additional catch-up periods; it is not an exact finish estimate.';
 $('heat_rate').textContent=ready&&d.heat_rate_ready&&finite(d.heat_rate)?(d.heat_rate>0?'+':'')+rateText(d.heat_rate):'Collecting readings';
 tick();buttons();
}
function renderCost(){
 const d=S.live;if(!d)return;
 const running=active(d),e=running?d.energy_accounting:d.last_firing_energy;
 $('cost_label').textContent=(running?'THIS FIRING':e?'LAST FIRING':'FIRING')+' · ESTIMATED COST';
 $('firing_cost').textContent=e&&finite(e.cost)?(e.currency_type||S.config.currency_type||'')+num(e.cost,2):running?'—':(S.config.currency_type||'')+'0.00';
 $('firing_energy').textContent=e&&finite(e.energy_kwh)?num(e.energy_kwh,3)+' kWh':running?'— kWh':'0.000 kWh';
 $('heater_on_time').textContent=duration(e&&e.heater_on_seconds);
 $('cost_formula').textContent=num(S.config.kw_elements,1)+' kW × heater on-hours × '+(S.config.currency_type||'')+num(S.config.kwh_rate,3)+'/kWh';
 if(!running&&e)$('cost_formula').textContent=finite(e.kw_elements)&&finite(e.kwh_rate)?num(e.kw_elements,1)+' kW × heater on-hours × '+e.currency_type+num(e.kwh_rate,3)+'/kWh':'Based on the power and tariff used for that firing.';
 $('cost_note').textContent=e&&e.history_incomplete?'Partial total: earlier heater on-time was unavailable.':e&&e.history_estimated?'Includes earlier heating estimated from controller logs.':e&&!running?'Final total · based on rated power and SSR on-time.':'Based on rated power; time with the heater off adds no cost.';
}
function tick(){
 const d=S.live;if(!d){connection();return;}
 const running=active(d),age=Math.max(0,(performance.now()-S.lastStatus)/1000);
 $('elapsed').textContent=duration(running?(d.elapsed_seconds||0)+Math.min(age,10):0);
 $('elapsed_label').textContent=d.elapsed_origin_known===false?'Elapsed since recovery':'Elapsed firing time';
 $('elapsed_note').textContent=running?d.elapsed_origin_known===false?'Original start time unavailable':'Includes pauses and catch-up time':'Hours · minutes · seconds';
 const t=running?Math.min(d.totaltime,(d.runtime||0)+(d.state==='RUNNING'&&!d.catching_up?Math.min(age,2):0)):0;
 $('program_time').textContent=duration(t);$('program_left').textContent=running?duration(Math.max(0,d.totaltime-t)):'—';
 const pct=running&&d.totaltime>0?clamp(t/d.totaltime*100,0,100):0;
 $('progress_label').textContent=num(pct,1)+'%';$('progress_fill').style.width=pct+'%';$('progress').setAttribute('aria-valuenow',pct.toFixed(1));
 $('updated').textContent=age<3?'Live · updated just now':'Last reading '+Math.floor(age)+'s ago';if(age>=10)connection();
}
function storage(d){
 if(Array.isArray(d)){
  S.profiles=d.filter(validProfile).sort((a,b)=>a.name.localeCompare(b.name));
  if(S.pendingStorage&&S.pendingStorage.type==='delete'&&!S.profiles.some(p=>p.name===S.pendingStorage.name))finishStorage('Program deleted.');
  const previous=S.selected||(S.live&&S.live.profile);$('profile_select').replaceChildren();
  S.profiles.forEach(p=>{const o=document.createElement('option');o.value=p.name;o.textContent=p.name;$('profile_select').append(o);});
  S.selected=S.profiles.some(p=>p.name===previous)?previous:S.profiles[0]?S.profiles[0].name:'';
  if(!S.profiles.length){const o=document.createElement('option');o.textContent='No programs yet';$('profile_select').append(o);}
  $('profile_select').value=S.selected;profileSummary();buttons();queueDraw();return;
 }
 if(d.resp&&S.pendingStorage){if(d.resp==='OK'&&S.pendingStorage.type==='save'){S.selected=S.pendingStorage.name;finishStorage('Program saved.');}else if(d.resp!=='OK'){clearTimeout(storageTimer);S.pendingStorage=null;editorError('The controller could not save this program. Your draft is still here.');}}
}
function profileSummary(){
 const p=selected();$('profile_duration').textContent=p?duration(p.data[p.data.length-1][0])+' duration':'— duration';
 $('profile_peak').textContent=p?num(Math.max(...p.data.map(v=>v[1])),0)+unit()+' peak':'— peak temperature';$('profile_segments').textContent=p?p.data.length-1+' segments':'— segments';
 $('schedule_body').replaceChildren();if(p)p.data.forEach((v,i)=>{
  const tr=document.createElement('tr'),r=i?(v[1]-p.data[i-1][1])/(v[0]-p.data[i-1][0])*3600:null;
  [i+1,duration(v[0]),num(v[1])+unit(),r===null?'Start':Math.abs(r)<.01?'Hold':(r>0?'+':'')+rateText(r)].forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.append(td);});$('schedule_body').append(tr);
 });
}
function queueDraw(){if(!drawPending){drawPending=true;requestAnimationFrame(()=>{drawPending=false;drawChart();});}}
function svg(tag,attrs={},text){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!==undefined)e.textContent=text;return e;}
function plannedTemperature(profile,seconds){
 if(!profile||!finite(seconds)||seconds<profile.data[0][0]||seconds>profile.data[profile.data.length-1][0])return null;
 const next=profile.data.findIndex(p=>p[0]>=seconds);if(next===0)return profile.data[0][1];
 const a=profile.data[next-1],b=profile.data[next];return a[1]+(b[1]-a[1])*(seconds-a[0])/(b[0]-a[0]);
}
function clipCurve(points,min,max){
 const clipped=[];
 points.forEach((p,i)=>{
  const previous=points[i-1];
  if(previous&&p.x!==previous.x){
   const crossings=[min,max].filter(t=>t>Math.min(previous.x,p.x)&&t<Math.max(previous.x,p.x));
   if(p.x<previous.x)crossings.reverse();
   crossings.forEach(t=>clipped.push({x:t,y:previous.y+(p.y-previous.y)*(t-previous.x)/(p.x-previous.x),interpolated:true}));
  }
  if(p.x>=min&&p.x<=max)clipped.push(p);
 });
 return clipped;
}
function resetChartZoom(){S.zoom=null;chartDrag=null;$('chart').removeAttribute('data-dragging');$('chart_tooltip').hidden=true;queueDraw();}
function setChartWindow(min,max,bounds=S.chart){
 if(!bounds)return;
 const full=bounds.fullMax-bounds.fullMin,span=clamp(max-min,Math.min(60,full),full),left=clamp(min,bounds.fullMin,bounds.fullMax-span);
 S.zoom=span>=full-.001?null:{min:left,max:left+span,fullMin:bounds.fullMin,fullMax:bounds.fullMax};
 $('chart_tooltip').hidden=true;queueDraw();
}
function zoomChart(factor,anchor){
 const g=S.chart;if(!g||(factor<1&&!g.hasCurve))return;
 const explicitAnchor=finite(anchor);
 if(!finite(anchor))anchor=!S.zoom&&g.hasActual&&finite(g.now)&&g.now>=g.minX&&g.now<=g.maxX?g.now:(g.minX+g.maxX)/2;
 const span=g.maxX-g.minX,newSpan=clamp(span*factor,Math.min(60,g.fullMax-g.fullMin),g.fullMax-g.fullMin);
 const ratio=(!explicitAnchor&&!S.zoom)?0.5:clamp((anchor-g.minX)/span,0,1);
 const left=anchor-newSpan*ratio;setChartWindow(left,left+newSpan);
}
function panChart(direction){const g=S.chart;if(!S.zoom||!g)return;const shift=(g.maxX-g.minX)*direction/2;setChartWindow(g.minX+shift,g.maxX+shift);}
function drawChart(){
 const root=$('chart'),w=Math.max(260,$('chart_wrap').clientWidth),h=$('chart_wrap').clientHeight;
 const pad={left:43,right:18,top:24,bottom:35},pw=w-pad.left-pad.right,ph=h-pad.top-pad.bottom;
 root.setAttribute('viewBox','0 0 '+w+' '+h);root.replaceChildren();
 const d=S.live,running=active(d),real=S.mode!=='program',recent=S.mode==='live',comparison=S.mode==='comparison';
 const retained=S.runProfile&&S.runProfile.name===(running?d.profile:S.selected);
 const profile=comparison?(running?(retained?S.runProfile:null):retained?S.runProfile:selected()):chartProfile();
 const relevant=running||recent||retained,origin=S.historyOrigin;
 const originKnown=!relevant||S.historyOriginKnown;
 const startPosition=!relevant?0:S.programStart&&S.programStart.origin===origin?S.programStart.seconds:null;
 const showPlan=!comparison||(originKnown&&finite(startPosition)),offset=comparison&&showPlan?startPosition:0,warmStart=comparison&&offset>0;
 const measured=(relevant?S.history:[]).map(p=>({x:real?(finite(p.elapsed)?p.elapsed:finite(origin)?p.timestamp-origin:null):p.runtime,y:p.temperature,target:p.target,timestamp:p.timestamp,elapsed:p.elapsed,kind:comparison?'Actual':'Measured'})).filter(p=>finite(p.x)&&p.x>=0);
 const lastElapsed=measured.length?measured[measured.length-1].x:0;
 const now=running?(real?d.elapsed_seconds:d.runtime):lastElapsed;
 let minX=0,maxX=showPlan&&profile?profile.data[profile.data.length-1][0]:3600;
 if(comparison){minX=showPlan&&profile&&S.showSkipped?Math.min(0,profile.data[0][0]-offset):0;maxX=Math.max(60,showPlan&&profile?maxX-offset:0,lastElapsed,finite(now)?now:0);}
 if(recent){maxX=Math.max(60,finite(now)?now:1800);minX=Math.max(0,maxX-1800);}
 if(!(maxX>minX))maxX=minX+60;
 const fullMin=S.zoom?Math.min(minX,S.zoom.fullMin):minX,fullMax=S.zoom?Math.max(maxX,S.zoom.fullMax):maxX;
 if(S.zoom){const span=Math.min(S.zoom.max-S.zoom.min,fullMax-fullMin);minX=clamp(S.zoom.min,fullMin,fullMax-span);maxX=minX+span;}
 const visible=clipCurve(measured,minX,maxX);
 let planned=recent?measured.filter(p=>finite(p.target)).map(p=>({x:p.x,y:p.target})):showPlan&&profile?profile.data.map(p=>({x:p[0]-offset,y:p[1]})):[];
 const startTemperature=warmStart?plannedTemperature(profile,offset):null;
 if(finite(startTemperature)&&!planned.some(p=>p.x===0)){planned.push({x:0,y:startTemperature});planned.sort((a,b)=>a.x-b.x);}
 if(warmStart&&!S.showSkipped)planned=planned.filter(p=>p.x>=0);
 planned=clipCurve(planned,minX,maxX);
 const temperatures=[...visible.map(p=>p.y),...planned.map(p=>p.y)];
 let yMin=0,yMax=temperatures.length?Math.max(...temperatures):300;
 if(recent&&temperatures.length)yMin=Math.max(0,Math.min(...temperatures)-10);
 if(warmStart&&!S.showSkipped&&temperatures.length)yMin=Math.max(0,Math.min(...temperatures)-20);
 if(S.zoom&&temperatures.length)yMin=Math.max(0,Math.min(...temperatures)-10);
 const spread=Math.max(20,yMax-yMin),rawStep=spread/4,magnitude=Math.pow(10,Math.floor(Math.log10(rawStep)));
 const step=[1,2,2.5,5,10].map(v=>v*magnitude).find(v=>v>=rawStep)||magnitude*10;
 yMin=Math.floor(yMin/step)*step;yMax=Math.ceil((yMax+spread*.08)/step)*step;if(yMax<=yMin)yMax=yMin+step*4;
 const x=v=>pad.left+(v-minX)/(maxX-minX)*pw,y=v=>pad.top+ph-(v-yMin)/(yMax-yMin)*ph;
 root.setAttribute('data-min-time',minX);root.setAttribute('data-max-time',maxX);root.setAttribute('data-full-min-time',fullMin);root.setAttribute('data-full-max-time',fullMax);root.classList.toggle('is-zoomed',!!S.zoom);
 root.append(svg('title',{},(running?d.profile+': ':'')+(comparison?'actual and original planned temperature':'measured and controller target temperature')+' over '+(real?originKnown?'elapsed firing time':'time since recovery':'program time')));
 const defs=svg('defs'),clip=svg('clipPath',{id:'plot-clip'});clip.append(svg('rect',{x:pad.left,y:pad.top,width:pw,height:ph}));defs.append(clip);
 const gradient=svg('linearGradient',{id:'temp-fill',x1:0,y1:0,x2:0,y2:1});
 gradient.append(svg('stop',{offset:'0%','stop-color':'#dc8b58','stop-opacity':'.12'}),svg('stop',{offset:'100%','stop-color':'#dc8b58','stop-opacity':'0'}));defs.append(gradient);root.append(defs);
 root.append(svg('text',{x:9,y:12,fill:'#8b978f','font-size':10},unit()));
 for(let t=yMin;t<=yMax+.0001;t+=step){
  const yy=y(t);root.append(svg('line',{x1:pad.left,y1:yy,x2:w-pad.right,y2:yy,stroke:'#e9eee7','stroke-width':1}));
  root.append(svg('text',{x:pad.left-10,y:yy+3,'text-anchor':'end',fill:'#8b978f','font-size':10},num(t,step<1?1:0)));
 }
 const ticks=w<450?4:6;
 let tickTimes=Array.from({length:ticks},(_,i)=>minX+(maxX-minX)*i/(ticks-1));
 if(warmStart&&minX<=0&&maxX>=0)tickTimes=[...tickTimes.filter(t=>Math.abs(x(t)-x(0))>55),0].sort((a,b)=>a-b);
 tickTimes.forEach(t=>root.append(svg('text',{x:x(t),y:h-10,'text-anchor':x(t)-pad.left<30?'start':w-pad.right-x(t)<30?'end':'middle',fill:t===0&&warmStart?'#365b50':'#8b978f','font-size':10,'font-weight':t===0&&warmStart?600:400},axisTime(t,warmStart,maxX-minX<300))));
 const plot=svg('g',{'clip-path':'url(#plot-clip)'}),path=points=>points.map((p,i)=>(i?'L':'M')+x(p.x).toFixed(2)+','+y(p.y).toFixed(2)).join(' ');
 if(visible.length>1)plot.append(svg('path',{d:path(visible)+' L'+x(visible[visible.length-1].x)+','+y(yMin)+' L'+x(visible[0].x)+','+y(yMin)+' Z',fill:'url(#temp-fill)'}));
 if(warmStart&&minX<=0&&maxX>=0)plot.append(svg('line',{'data-marker':'start',x1:x(0),y1:pad.top,x2:x(0),y2:pad.top+ph,stroke:'#a1b5a9','stroke-dasharray':'2 4'}));
 if(planned.length)plot.append(svg('path',{'data-series':'planned',d:path(planned),fill:'none',stroke:'#548e7a','stroke-width':2,'stroke-dasharray':'5 5','stroke-linejoin':'round'}));
 if(!recent)planned.filter(p=>!p.interpolated).forEach(p=>plot.append(svg('circle',{cx:x(p.x),cy:y(p.y),r:3,fill:'#fff',stroke:'#548e7a','stroke-width':1.5})));
 const readings=visible.filter(p=>!p.interpolated);
 if(visible.length){plot.append(svg('path',{'data-series':'actual',d:path(visible),fill:'none',stroke:'#d97842','stroke-width':2.5,'stroke-linecap':'round','stroke-linejoin':'round'}));const last=readings[readings.length-1];if(last)plot.append(svg('circle',{cx:x(last.x),cy:y(last.y),r:4,fill:'#d97842',stroke:'#fff','stroke-width':2}));}
 if(running&&!recent&&finite(now)&&now>=minX&&now<=maxX){const xx=x(now);plot.append(svg('line',{'data-marker':'now',x1:xx,y1:pad.top,x2:xx,y2:pad.top+ph,stroke:'#c6cfc7','stroke-dasharray':'3 4'}));root.append(svg('text',{x:clamp(xx+5,pad.left,w-42),y:17,fill:'#7e8e83','font-size':10},'Now'));}
 root.append(plot);
 if(!visible.length&&!planned.length)root.append(svg('text',{x:w/2,y:h/2,'text-anchor':'middle',fill:'#95a198','font-size':12},'Temperature readings will appear here'));
 S.chart={points:[...readings,...planned.map(p=>({...p,kind:comparison?'Planned':recent?'Controller target':'Planned'}))].sort((a,b)=>a.x-b.x),x,y,width:w,height:h,minX,maxX,fullMin,fullMax,now,hasActual:measured.length>0,hasCurve:!!(visible.length||planned.length),pad,pw,real,comparison,profile:showPlan?profile:null,originKnown,offset,warmStart};
 $('zoom_in').disabled=(!visible.length&&!planned.length)||maxX-minX<=Math.min(60,fullMax-fullMin)+.001;
 $('zoom_out').disabled=$('zoom_reset').disabled=!S.zoom;
 $('pan_left').disabled=!S.zoom||minX<=fullMin+.001;$('pan_right').disabled=!S.zoom||maxX>=fullMax-.001;
 $('zoom_level').textContent=S.zoom?axisTime(maxX-minX)+' view':'Full view';
 $('actual_legend').textContent=comparison?'Actual':'Measured';$('planned_legend_label').textContent=recent?'Controller target':'Planned';$('planned_legend').hidden=comparison&&!showPlan;
 $('warm_start_note').hidden=!warmStart;
 const actualStart=warmStart?S.programStart.temperature:null;
 $('warm_start_summary').textContent=warmStart?((finite(actualStart)?'Started at '+num(actualStart)+unit():finite(startTemperature)?'Program starts at '+num(startTemperature)+unit():'Started partway through the program')+' · '+axisTime(offset)+' skipped'):'';
 $('show_skipped').textContent=S.showSkipped?'Hide skipped steps':'Show skipped steps';$('show_skipped').setAttribute('aria-expanded',String(S.showSkipped));
 $('chart_summary').textContent=S.history.length?S.history.length+' available readings':'Live readings appear during firing';
 $('chart_hint').textContent=comparison?(!originKnown?'Time since recovery · Original start unknown; plan comparison unavailable':!finite(startPosition)?'Starting program position unavailable; plan comparison unavailable':warmStart?(S.showSkipped?'0 = firing start · Negative time = skipped program':'Time since firing start · Hover or touch to inspect'):'Elapsed time from firing start · Original plan includes no added waits'):(real?originKnown?'Elapsed firing time':'Time since recovery':'Program time')+' · Hover or touch to inspect';
}
function tooltip(index){
 const g=S.chart;if(!g||!g.points.length)return;index=clamp(index,0,g.points.length-1);g.cursor=index;
 const p=g.points[index],tip=$('chart_tooltip');tip.replaceChildren();
 const title=document.createElement('strong');title.textContent=(g.warmStart?'Time ':g.real?g.originKnown?'Elapsed ':'Since recovery ':'Program ')+(g.maxX-g.minX<300?axisTime(p.x,g.warmStart,true):g.warmStart?signedTime(p.x):hoursMinutes(p.x));
 const a=document.createElement('div');a.textContent=p.kind+' '+num(p.y)+unit();tip.append(title,a);
 if(g.comparison&&p.kind==='Actual'){
  const planned=plannedTemperature(g.profile,p.x+g.offset),b=document.createElement('div');
  if(finite(planned)){b.textContent='Planned '+num(planned)+unit();tip.append(b);const delta=document.createElement('div');delta.textContent=Math.abs(p.y-planned)<.1?'On the planned ramp':num(Math.abs(p.y-planned))+unit()+(p.y<planned?' below plan':' above plan');tip.append(delta);}
  else if(g.profile&&p.x>g.profile.data[g.profile.data.length-1][0]-g.offset){const finish=g.profile.data[g.profile.data.length-1][0]-g.offset;b.textContent='Planned finish: '+(g.warmStart?signedTime(finish):hoursMinutes(finish));tip.append(b);}
 }else if(p.kind==='Measured'&&finite(p.target)){const b=document.createElement('div');b.textContent='Controller target '+num(p.target)+unit();tip.append(b);}
 if(!g.real&&finite(p.elapsed)){const e=document.createElement('div');e.textContent='Elapsed '+hoursMinutes(p.elapsed);tip.append(e);}
 tip.hidden=false;tip.style.left=clamp(g.x(p.x)+10,4,g.width-tip.offsetWidth-4)+'px';tip.style.top=clamp(g.y(p.y)-tip.offsetHeight-10,2,g.height-tip.offsetHeight-2)+'px';
}
$('chart').addEventListener('pointermove',e=>{
 const g=S.chart;if(!g)return;const rect=$('chart').getBoundingClientRect();
 if(chartDrag&&Math.abs(e.clientX-chartDrag.x)>=4){const shift=-(e.clientX-chartDrag.x)/rect.width*g.width/g.pw*(chartDrag.max-chartDrag.min);setChartWindow(chartDrag.min+shift,chartDrag.max+shift,chartDrag);return;}
 if(!g.points.length)return;const xx=(e.clientX-rect.left)/rect.width*g.width,yy=(e.clientY-rect.top)/rect.height*g.height;
 const distance=p=>(g.x(p.x)-xx)**2+(g.y(p.y)-yy)**2;
 let i=0;g.points.forEach((p,j)=>{if(distance(p)<distance(g.points[i]))i=j;});tooltip(i);
});
$('chart').addEventListener('pointerleave',()=>{$('chart_tooltip').hidden=true;});
$('chart').addEventListener('pointerdown',e=>{if(!S.zoom||!S.chart||e.button!==0||!e.isPrimary)return;const g=S.chart;chartDrag={x:e.clientX,min:g.minX,max:g.maxX,fullMin:g.fullMin,fullMax:g.fullMax};$('chart').setPointerCapture(e.pointerId);$('chart').setAttribute('data-dragging','true');});
function endChartDrag(e){chartDrag=null;$('chart').removeAttribute('data-dragging');if($('chart').hasPointerCapture(e.pointerId))$('chart').releasePointerCapture(e.pointerId);}
$('chart').addEventListener('pointerup',endChartDrag);$('chart').addEventListener('pointercancel',endChartDrag);
$('chart').addEventListener('wheel',e=>{const g=S.chart;if(!e.ctrlKey||!g||!g.hasCurve)return;e.preventDefault();const rect=$('chart').getBoundingClientRect(),fraction=clamp(((e.clientX-rect.left)/rect.width*g.width-g.pad.left)/g.pw,0,1);zoomChart(e.deltaY<0?0.8:1.25,g.minX+fraction*(g.maxX-g.minX));},{passive:false});
$('chart').addEventListener('keydown',e=>{
 if(e.ctrlKey||e.metaKey||e.altKey)return;
 if(['+','=','-','_','0'].includes(e.key)){e.preventDefault();if(e.key==='0')resetChartZoom();else zoomChart(['+','='].includes(e.key)?0.5:2);return;}
 if(['ArrowLeft','ArrowRight'].includes(e.key)&&S.chart){e.preventDefault();if(e.shiftKey)panChart(e.key==='ArrowRight'?1:-1);else if(S.chart.points.length)tooltip((S.chart.cursor===undefined?S.chart.points.length-1:S.chart.cursor)+(e.key==='ArrowRight'?1:-1));}
 if(e.key==='Escape')$('chart_tooltip').hidden=true;
});
$('zoom_in').onclick=()=>zoomChart(.5);$('zoom_out').onclick=()=>zoomChart(2);$('zoom_reset').onclick=resetChartZoom;
$('pan_left').onclick=()=>panChart(-1);$('pan_right').onclick=()=>panChart(1);
function mode(value){S.mode=value;resetChartZoom();['comparison','program','live'].forEach(name=>$('view_'+name).setAttribute('aria-pressed',value===name));}
$('view_comparison').onclick=()=>mode('comparison');$('view_program').onclick=()=>mode('program');$('view_live').onclick=()=>mode('live');
$('show_skipped').onclick=()=>{S.showSkipped=!S.showSkipped;resetChartZoom();};
$('profile_select').onchange=()=>{S.selected=$('profile_select').value;resetChartZoom();profileSummary();buttons();};
$('schedule_button').onclick=()=>{$('schedule_container').hidden=!$('schedule_container').hidden;$('schedule_button').textContent=$('schedule_container').hidden?'View schedule ↓':'Hide schedule ↑';};
$('export_button').onclick=()=>{
 const rows=[['timestamp_utc','elapsed_seconds','program_seconds','measured_'+unit(),'target_'+unit()]];
 S.history.forEach(p=>rows.push([new Date(p.timestamp*1000).toISOString(),p.elapsed===null?'':p.elapsed,p.runtime,p.temperature,p.target]));
 const url=URL.createObjectURL(new Blob([rows.map(r=>r.join(',')).join('\n')],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');
 a.href=url;a.download='kiln-readings-'+new Date().toISOString().slice(0,10)+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
function confirmAction(title,message,label,callback,danger=false,details=[]){
 $('confirm_title').textContent=title;$('confirm_text').textContent=message;$('confirm_action').textContent=label;$('confirm_action').className='button '+(danger?'danger':'primary');$('confirm_details').replaceChildren();
 details.forEach(([key,value])=>{const row=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key;dd.textContent=value;row.append(dt,dd);$('confirm_details').append(row);});
 S.confirm=callback;$('confirmation').showModal();
}
$('confirm_cancel').onclick=$('confirm_close').onclick=()=>{$('confirmation').close();S.confirm=null;};
$('confirm_action').onclick=()=>{const callback=S.confirm;S.confirm=null;$('confirmation').close();if(callback)callback();};
$('confirmation').addEventListener('cancel',()=>{S.confirm=null;});
async function command(cmd,profile){
 if(!fresh()){toast('Reconnect before sending a command.');return;}
 try{
  const response=await fetch('/api/health',{cache:'no-store'});if(!response.ok)throw new Error('Cannot check controller state.');
  const current=await response.json();
  if(cmd==='run'&&(current.state!=='IDLE'||current.sensor_ready===false))throw new Error('The kiln must be idle with a ready sensor before starting.');
  if(cmd==='stop'&&!active(current)){toast('The kiln is already idle.');return;}
  S.pendingState=cmd==='run'?'RUNNING':'IDLE';buttons();
  const result=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({cmd,profile})});
  const body=await result.json();if(!result.ok||!body.success)throw new Error(body.error||'Command was not accepted.');
  toast(cmd==='run'?'Start requested. Waiting for the controller…':'Stop requested. Waiting for the controller…');
  commandTimer=setTimeout(()=>{if(S.pendingState){S.pendingState=null;buttons();toast('No state change confirmed. Check the controller before trying again.');}},12000);
 }catch(error){S.pendingState=null;buttons();toast(error.message||'Connection lost. Check the kiln state before trying again.');}
}
$('start_button').onclick=()=>{
 const p=selected();if(!p)return;
 confirmAction('Start this firing?',S.config.seek_start?'The controller may skip the initial part of the schedule if the kiln is already warm.':'The controller will follow this program from its beginning.','Start firing',()=>command('run',p.name),false,[['Program',p.name],['Scheduled duration',duration(p.data[p.data.length-1][0])],['Peak temperature',num(Math.max(...p.data.map(v=>v[1])),0)+unit()]]);
};
$('stop_button').onclick=()=>confirmAction('Stop the current firing?','Heating will switch off and automatic recovery of this firing will be cancelled. The kiln will cool naturally.','Stop firing',()=>command('stop'),true);
function editorError(message){$('editor_error').textContent=message;$('editor_error').hidden=!message;buttons();}
function editorPoints(){return [...$('editor_rows').rows].map(row=>[Number(row.querySelector('.point-time').value)*timeFactor(S.config.time_scale_profile),Number(row.querySelector('.point-temp').value)]);}
function editorRates(){
 const points=editorPoints();[...$('editor_rows').rows].forEach((row,i)=>{
  if(!i)return;const rate=(points[i][1]-points[i-1][1])/(points[i][0]-points[i-1][0])*timeFactor(S.config.time_scale_slope||'h');
  const input=row.querySelector('.point-rate-input');input.value=finite(rate)?Number(rate.toFixed(3)):'';input.setCustomValidity('');
 });rampWarnings(points);
}
function rampWarnings(points){
 const box=$('ramp_warning');box.replaceChildren();let unknown=false,exceeded=0;
 const bands=firingOverview&&firingOverview.summary.ramps||[];
 [...$('editor_rows').rows].forEach(row=>row.classList.remove('rate-exceeded'));
 points.forEach((p,i)=>{
  if(!i||p[1]<=points[i-1][1]||p[0]<=points[i-1][0])return;
  const toC=v=>S.config.temp_scale==='f'?(v-32)*5/9:v,from=toC(points[i-1][1]),to=toC(p[1]),requested=(to-from)/(p[0]-points[i-1][0])*3600;
  const relevant=bands.filter(b=>b.from_c<to&&b.to_c>from);
  let covered=from;for(const b of relevant){if(b.from_c>covered+.01)break;covered=Math.max(covered,b.to_c);}if(covered<to-.01)unknown=true;
  const limited=relevant.filter(b=>requested>b.max_rate_c_hour*1.005).sort((a,b)=>a.max_rate_c_hour-b.max_rate_c_hour);
  if(limited.length){
   exceeded++;$('editor_rows').rows[i].classList.add('rate-exceeded');const b=limited[0],f=S.config.temp_scale==='f'?1.8:1,toDisplay=v=>S.config.temp_scale==='f'?v*1.8+32:v;
   const p=document.createElement('p');p.textContent='Point '+(i+1)+': requested '+rateText(requested*f)+' exceeds this kiln’s recorded maximum of '+rateText(b.max_rate_c_hour*f)+' in the '+num(toDisplay(b.from_c),0)+'–'+num(toDisplay(b.to_c),0)+unit()+' range.';box.append(p);
  }
 });
 if(exceeded){const p=document.createElement('p');p.textContent='A slower rate may reduce catch-up time. This is measured guidance; load and kiln condition affect performance. You can still save your program.';box.append(p);}
 box.hidden=!exceeded;
 $('ramp_learning').textContent=!firingOverview?'Ramp data unavailable. Reconnecting to firing history…':!bands.length?'Learning your kiln: no sustained full-power ramp measurements yet.':unknown?'Some temperature ranges are not yet measured. Rates are checked only where this kiln has data.':'Rates checked against this kiln’s sustained full-power measurements.';
}
async function loadFiringOverview(){
 try{const r=await fetch('/api/firings',{cache:'no-store'});if(!r.ok)throw new Error();firingOverview=await r.json();if($('editor').open)rampWarnings(editorPoints());}catch(_){firingOverview=null;if($('editor').open)rampWarnings(editorPoints());}
}
async function loadFiringHistory(){
 if(!S.config.temp_scale||!S.live||!active(S.live)||historyLoading||loadedFiring===S.runKey)return;
 const key=S.runKey;historyLoading=key;
 try{
  const r=await fetch('/api/firings',{cache:'no-store'});if(!r.ok)throw new Error();const overview=await r.json();firingOverview=overview;
  const record=overview.records.find(r=>r.started_at===S.live.run_started_at&&r.profile===S.live.profile);if(!record)return;
  const response=await fetch('/api/firings/'+record.id,{cache:'no-store'});if(!response.ok)throw new Error();const data=await response.json();
  if(S.runKey!==key)return;
  const scale=S.config.temp_scale||'c',convert=v=>scale==='f'?v*1.8+32:v;
  if(data.record&&validProfile(data.record.profile_data))S.runProfile={...data.record.profile_data,data:data.record.profile_data.data.map(p=>[p[0],convert(p[1])])};
  const first=data.samples[0];if(first&&data.record)rememberProgramStart({runtime:first.program_seconds,elapsed_seconds:first.elapsed_seconds,timestamp:first.timestamp,run_started_at:data.record.started_at,source:first.source,temperature:finite(first.temperature_c)?convert(first.temperature_c):null,sensor_ready:first.sensor_ready});
  const saved=data.samples.filter(p=>p.sensor_ready&&finite(p.temperature_c)).map(p=>({timestamp:p.timestamp,runtime:p.program_seconds,temperature:convert(p.temperature_c),target:finite(p.target_c)?convert(p.target_c):null,elapsed:p.elapsed_seconds}));
  const merged=[...saved,...S.history].sort((a,b)=>a.timestamp-b.timestamp).filter((p,i,a)=>!i||p.timestamp>a[i-1].timestamp);
  const stride=Math.max(1,Math.ceil(merged.length/4000));S.history=merged.filter((_,i)=>i%stride===0||i===merged.length-1);loadedFiring=key;queueDraw();buttons();
 }catch(_){}finally{historyLoading=null;}
}
loadFiringOverview();setInterval(loadFiringOverview,60000);
function editorRows(points){
 $('editor_rows').replaceChildren();points.forEach((point,i)=>{
  const row=document.createElement('tr'),tdTime=document.createElement('td'),time=document.createElement('input');
  time.type='number';time.min='0';time.step='any';time.required=true;time.value=Number((point[0]/timeFactor(S.config.time_scale_profile)).toFixed(6));time.className='point-time';time.setAttribute('aria-label','Point '+(i+1)+' time in '+timeWord(S.config.time_scale_profile));if(i===0)time.readOnly=true;
  const tdTemp=document.createElement('td'),temp=document.createElement('input');
  temp.type='number';temp.step='any';temp.required=true;temp.value=Number(point[1].toFixed(3));temp.min='0';if(finite(S.config.emergency_shutoff_temp))temp.max=S.config.emergency_shutoff_temp;temp.className='point-temp';temp.setAttribute('aria-label','Point '+(i+1)+' temperature');
  const rate=document.createElement('td');rate.className='point-rate';
  if(i){const input=document.createElement('input');input.type='number';input.step='any';input.className='point-rate-input';input.setAttribute('aria-label','Point '+(i+1)+' rate per '+(S.config.time_scale_slope||'h'));
   input.onchange=()=>{const current=editorPoints(),delta=current[i][1]-current[i-1][1],r=Number(input.value),dt=delta/r*timeFactor(S.config.time_scale_slope||'h');
    if(delta===0&&r===0){editorRates();return;}if(!finite(dt)||dt<=0){input.setCustomValidity('Use a positive rate for heating or a negative rate for cooling. Set hold duration using time.');input.reportValidity();return;}
    const shift=current[i-1][0]+dt-current[i][0];[...$('editor_rows').rows].forEach((row,j)=>{if(j>=i)row.querySelector('.point-time').value=Number(((current[j][0]+shift)/timeFactor(S.config.time_scale_profile)).toFixed(6));});S.dirty=true;editorRates();
   };rate.append(input);
  }else rate.textContent='Start';const tdDelete=document.createElement('td'),remove=document.createElement('button');
  remove.type='button';remove.className='icon-button destructive';remove.textContent='×';remove.setAttribute('aria-label','Remove point '+(i+1));remove.disabled=i===0||points.length<=2;
  remove.onclick=()=>{const current=editorPoints();current.splice(i,1);editorRows(current);S.dirty=true;};time.oninput=temp.oninput=()=>{S.dirty=true;editorRates();};
  tdTime.append(time);tdTemp.append(temp);tdDelete.append(remove);row.append(tdTime,tdTemp,rate,tdDelete);$('editor_rows').append(row);
 });editorRates();
}
function openEditor(p){
 S.editorProfile=p?JSON.parse(JSON.stringify(p)):null;S.dirty=false;$('editor_title').textContent=p?'Edit program':'New program';$('program_name').value=p?p.name:'';$('delete_button').hidden=!p;
 $('editor_active_note').hidden=!(p&&active(S.live)&&p.name===S.live.profile);
 const start=S.config.temp_scale==='f'?68:20;editorRows(p?p.data:[[0,start],[3600,start+100],[5400,start+100]]);editorError('');$('editor').showModal();$('program_name').focus();loadFiringOverview();
}
function closeEditor(){
 if(S.pendingStorage){toast('Wait for the controller to confirm the change.');return;}
 if(S.dirty)confirmAction('Discard unsaved changes?','Your saved program will stay unchanged.','Discard draft',()=>{$('editor').close();S.dirty=false;});
 else $('editor').close();
}
$('new_button').onclick=()=>openEditor(null);$('edit_button').onclick=()=>openEditor(selected());$('program_name').oninput=()=>{S.dirty=true;};
$('editor_close').onclick=$('editor_cancel').onclick=closeEditor;$('editor').addEventListener('cancel',e=>{e.preventDefault();closeEditor();});
$('add_point').onclick=()=>{const points=editorPoints(),last=points[points.length-1];points.push([last[0]+3600,last[1]]);editorRows(points);S.dirty=true;};
function sendStorage(type,profile){
 if(!S.ready.storage||S.pendingStorage){editorError('Wait for the storage connection before saving.');return;}
 S.pendingStorage={type,name:profile.name};editorError('');S.sockets.storage.send(JSON.stringify({cmd:type==='save'?'PUT':'DELETE',profile}));
 storageTimer=setTimeout(()=>{S.pendingStorage=null;editorError('No confirmation received. Check the program list before trying again.');},10000);
 if(type==='delete')setTimeout(()=>{if(S.ready.storage)S.sockets.storage.send('GET');},1200);
}
function finishStorage(message){clearTimeout(storageTimer);S.pendingStorage=null;S.dirty=false;if($('editor').open)$('editor').close();toast(message);buttons();}
$('editor_form').onsubmit=e=>{
 e.preventDefault();const name=$('program_name').value.trim(),points=editorPoints();
 if(!name||/[\/\\\u0000-\u001f]/.test(name)||name==='.'||name==='..'){editorError('Use a name without slashes or control characters.');return;}
 if(points[0][0]!==0||points.some((p,i)=>!finite(p[0])||!finite(p[1])||p[0]<0||p[1]<0||(i&&p[0]<=points[i-1][0]))){editorError('Start at time 0 and use increasing times with valid temperatures.');return;}
 if(finite(S.config.emergency_shutoff_temp)&&points.some(p=>p[1]>S.config.emergency_shutoff_temp)){editorError('A target cannot exceed the configured temperature limit.');return;}
 const profile=Object.assign({},S.editorProfile||{type:'profile'},{name,data:points,temp_units:S.config.temp_scale||'c'});
 const replacement=S.profiles.some(p=>p.name===name)&&(!S.editorProfile||S.editorProfile.name!==name);
 if(replacement)confirmAction('Replace an existing program?','A saved program named '+name+' already exists.','Replace program',()=>sendStorage('save',profile));
 else sendStorage('save',profile);
};
$('delete_button').onclick=()=>{
 const p=S.editorProfile;if(!p)return;if(active(S.live)&&S.live.profile===p.name){editorError('The current firing’s program cannot be deleted.');return;}
 confirmAction('Delete this program?',p.name+' will be removed from your saved programs.','Delete program',()=>sendStorage('delete',p),true);
};
new ResizeObserver(queueDraw).observe($('chart_wrap'));
['status','config','storage'].forEach(connect);setInterval(tick,1000);queueDraw();
})();
