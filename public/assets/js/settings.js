(() => {
'use strict';
const $=id=>document.getElementById(id);
let data=null,draft={},section='general',busy=false,lastSeen=0,reviewAction=null,reviewSnapshot=null,toastTimer;
const descriptions={general:'Power, electricity pricing and the units shown throughout your dashboard.',firing:'How the controller follows a schedule and limits low-temperature heating.',pid:'Tune temperature response for your kiln. Units follow the selected temperature scale.',sensor:'Thermocouple configuration and the physical pins used by your Orange Pi.',recovery:'Choose when a saved firing can resume after a power interruption.',protection:'These settings change how the controller responds to temperature and sensor faults.',system:'Web access, diagnostics and the files used to store programs and recovery state.',simulation:'Values for the virtual kiln. They do not describe the physical kiln when simulation is off.',legacy:'Retained configuration values that the current controller no longer uses.'};
const absTemps=['emergency_shutoff_temp','throttle_below_temp','sim_t_env'],deltaTemps=['thermocouple_offset','pid_control_window','catch_up_tolerance'];
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const dirty=()=>data&&!equal(draft,data.values);
const fresh=()=>Date.now()-lastSeen<12000;
const changed=(a,b)=>data.schema.filter(f=>!equal(a[f.key],b[f.key]));
function message(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>{$('toast').hidden=true;},6000);}
function failure(text){$('settings_error').textContent=text;$('settings_error').hidden=!text;}
function display(f,value){if(f.type==='boolean')return value?'Enabled':'Disabled';if(f.options)return f.options[value]||String(value);return String(value);}
function updateActions(){
 if(!data)return;const edits=changed(draft,data.values),pending=changed(data.values,data.current);
 $('changes_title').textContent=edits.length?edits.length+' unsaved '+(edits.length===1?'change':'changes'):pending.length?pending.length+' saved '+(pending.length===1?'change':'changes')+' waiting to apply':'All settings applied';
 $('changes_note').textContent=data.state!=='IDLE'?'The current firing keeps its existing settings. Apply saved changes when the kiln is idle.':'Saving keeps changes pending. Apply & restart activates them.';
 $('save_settings').disabled=!fresh()||busy||!edits.length;
 $('apply_settings').disabled=!fresh()||busy||!!edits.length||!pending.length||!data.can_apply;
 $('discard_settings').disabled=!fresh()||busy||(!edits.length&&!pending.length);
 $('export_settings').disabled=busy;
 $('controller_state').textContent=!fresh()?'Disconnected':data.state==='IDLE'?'Kiln idle':data.state==='PAUSED'?'Firing paused':'Firing in progress';
 $('controller_state').className='state-pill'+(data.state==='IDLE'?'':' running');
 $('status_title').textContent=!fresh()?'Connection lost':pending.length?'Saved changes are waiting':data.state==='IDLE'?'Your kiln is ready for configuration':'Your firing is continuing';
 $('status_detail').textContent=!fresh()?'Reconnect before saving or applying settings. Your draft stays on this page.':pending.length?'The controller continues using its current settings until you choose Apply & restart.':data.state==='IDLE'?'Review and save your changes, then apply them with a short controller restart.':'You can edit and save settings now. Applying them is available once the kiln is idle.';
 $('settings_status').classList.toggle('pending',pending.length>0);
 document.querySelectorAll('.setting-field').forEach(row=>{const k=row.dataset.key;row.classList.toggle('is-dirty',!equal(draft[k],data.values[k]));row.classList.toggle('is-pending',!equal(data.values[k],data.current[k]));});
}
function unitLabels(){document.querySelectorAll('.setting-unit').forEach(e=>{e.textContent='°'+draft.temp_scale.toUpperCase();});}
function changeUnits(oldUnit,newUnit){
 if(oldUnit===newUnit)return;
 const factor=newUnit==='f'?1.8:1/1.8;
 absTemps.forEach(k=>{draft[k]=newUnit==='f'?draft[k]*1.8+32:(draft[k]-32)/1.8;});
 deltaTemps.forEach(k=>{draft[k]*=factor;});draft.pid_kp/=factor;draft.pid_kd/=factor;draft.pid_ki*=factor;
 [...absTemps,...deltaTemps,'pid_kp','pid_ki','pid_kd'].forEach(k=>{draft[k]=Number(draft[k].toFixed(6));$('setting_'+k).value=draft[k];});
 unitLabels();message('Temperature limits, calibration and PID gains converted to '+(newUnit==='f'?'Fahrenheit.':'Celsius.'));
}
function render(){
 $('settings_nav').replaceChildren();$('settings_groups').replaceChildren();
 data.groups.forEach(group=>{
  const fields=data.schema.filter(f=>f.group===group.key),nav=document.createElement('button');nav.type='button';nav.dataset.group=group.key;nav.setAttribute('aria-current',group.key===section);nav.append(document.createTextNode(group.label));const count=document.createElement('small');count.textContent=fields.length;nav.append(count);nav.onclick=()=>{section=group.key;$('settings_search').value='';filter();};$('settings_nav').append(nav);
  const card=document.createElement('section');card.className='card settings-section';card.dataset.group=group.key;
  const heading=document.createElement('div');heading.className='settings-section-heading';const eye=document.createElement('div');eye.className='eyebrow';eye.textContent=group.key==='general'?'YOUR PREFERENCES':'CONTROLLER CONFIGURATION';const title=document.createElement('h2');title.textContent=group.label;const desc=document.createElement('p');desc.textContent=descriptions[group.key];heading.append(eye,title,desc);
  if(group.key==='protection'){const note=document.createElement('div');note.className='notice warning';note.textContent='Keep fault overrides off for normal operation. Enabling an override allows operation despite that fault.';heading.append(note);}
  card.append(heading);
  fields.forEach(f=>{
   const row=document.createElement('div');row.className='setting-field'+(f.type==='boolean'?' boolean-field':'');row.dataset.key=f.key;
   const text=document.createElement('div'),label=document.createElement('label');label.className='setting-label';label.htmlFor='setting_'+f.key;label.textContent=f.label;text.append(label);
   if(f.help){const help=document.createElement('p');help.className='setting-help';help.id='help_'+f.key;help.textContent=f.help;text.append(help);}
   const key=document.createElement('div');key.className='setting-key';key.textContent=f.key;text.append(key);
   if(f.readonly){const managed=document.createElement('p');managed.className='setting-managed';managed.textContent=f.readonly;text.append(managed);}
   const box=document.createElement('div');box.className='setting-control';let input;
   if(absTemps.includes(f.key)||deltaTemps.includes(f.key)){const unit=document.createElement('span');unit.className='setting-unit';box.append(unit);}
   if(f.options){input=document.createElement('select');Object.entries(f.options).forEach(([v,t])=>{const option=document.createElement('option');option.value=v;option.textContent=t;input.append(option);});input.value=draft[f.key];}
   else{input=document.createElement('input');input.type=f.type==='boolean'?'checkbox':['number','integer'].includes(f.type)?'number':'text';if(f.type==='boolean')input.checked=draft[f.key];else input.value=draft[f.key];if(input.type==='number'){input.step=f.type==='integer'?'1':'any';if(f.min!==undefined)input.min=f.min;if(f.max!==undefined)input.max=f.max;}else if(input.type==='text')input.maxLength=f.key==='currency_type'?8:250;}
   input.id='setting_'+f.key;input.setAttribute('aria-label',f.label);input.disabled=!!f.readonly;if(f.help)input.setAttribute('aria-describedby','help_'+f.key);
   input.addEventListener('input',()=>{const old=draft[f.key];draft[f.key]=f.type==='boolean'?input.checked:['number','integer'].includes(f.type)?input.value===''?null:Number(input.value):input.value;if(f.key==='temp_scale')changeUnits(old,draft[f.key]);row.classList.remove('invalid');row.querySelector('.setting-error').textContent='';updateActions();});
   const error=document.createElement('p');error.className='setting-error';error.id='error_'+f.key;box.append(input,error);row.append(text,box);card.append(row);
  });$('settings_groups').append(card);
 });unitLabels();filter();updateActions();
}
function filter(){
 const q=$('settings_search').value.toLowerCase().trim();let total=0;
 document.querySelectorAll('.settings-section').forEach(card=>{let count=0;card.querySelectorAll('.setting-field').forEach(row=>{const f=data.schema.find(f=>f.key===row.dataset.key),match=!q||[f.key,f.label,f.help].join(' ').toLowerCase().includes(q);row.hidden=!match;if(match)count++;});card.hidden=q?!count:card.dataset.group!==section;if(!card.hidden)total+=count;});
 document.querySelectorAll('.settings-nav button').forEach(b=>b.setAttribute('aria-current',!q&&b.dataset.group===section));$('empty_results').hidden=total>0;
}
function review(kind){
 const fields=kind==='save'?changed(draft,data.values):changed(data.values,data.current);
 $('review_rows').replaceChildren();fields.forEach(f=>{const tr=document.createElement('tr');[f.label,display(f,kind==='save'?data.values[f.key]:data.current[f.key]),display(f,kind==='save'?draft[f.key]:data.values[f.key])].forEach(text=>{const td=document.createElement('td');td.textContent=text;tr.append(td);});$('review_rows').append(tr);});
 $('review_title').textContent=kind==='save'?'Save these settings?':kind==='discard'?'Discard saved changes?':'Apply settings and restart?';
 $('review_note').textContent=kind==='save'?'These changes are saved for later. The running controller and current firing are unchanged.':kind==='discard'?'The controller will continue using its currently applied settings.':'The kiln is idle. The controller will restart with these values. Check that any sensor and SSR wiring matches the selected pins.';
 $('review_confirm').textContent=kind==='save'?'Save for later':kind==='discard'?'Discard saved changes':'Apply & restart';
 reviewAction=kind;reviewSnapshot={revision:data.revision,token:data.token,values:structuredClone(draft)};$('settings_review').showModal();
}
async function mutate(kind,snapshot){
 if(busy||!fresh())return;busy=true;updateActions();failure('');
 try{
  const response=await fetch('/api/settings'+(kind==='save'?'':'/'+kind),{method:'POST',headers:{'Content-Type':'application/json','X-Kiln-Settings':snapshot.token},body:JSON.stringify({revision:snapshot.revision,...(kind==='save'?{values:snapshot.values}:{})})});
  const result=await response.json();
  if(!response.ok){
   if(result.fields){Object.entries(result.fields).forEach(([key,message])=>{const row=document.querySelector('.setting-field[data-key="'+key+'"]');if(row){row.classList.add('invalid');row.querySelector('.setting-error').textContent=message;}});const first=Object.keys(result.fields).find(k=>data.schema.some(f=>f.key===k));if(first){section=data.schema.find(f=>f.key===first).group;$('settings_search').value='';filter();$('setting_'+first).focus();}}
   throw new Error(result.error||'The change was not accepted.');
  }
  if(kind==='apply'){
   $('status_title').textContent='Restarting the controller…';$('status_detail').textContent='Reconnecting with your saved settings. This usually takes a few seconds.';
   const url=new URL(location.href);url.port=String(result.port);url.searchParams.set('applied',String(Date.now()));
   if(url.port!==location.port){$('status_detail').replaceChildren(document.createTextNode('The dashboard is moving to port '+result.port+'. '));const link=document.createElement('a');link.href=url.href;link.textContent='Open settings on the new port';$('status_detail').append(link);setTimeout(()=>{location.href=url.href;},7000);return;}
   const oldToken=data.token;await new Promise(resolve=>setTimeout(resolve,2500));
   for(let i=0;i<25;i++){try{const r=await fetch('/api/settings',{cache:'no-store'});const next=await r.json();if(r.ok&&next.token!==oldToken){data=next;draft=structuredClone(data.values);lastSeen=Date.now();render();message('Settings applied. The controller is ready.');return;}}catch(_){}await new Promise(resolve=>setTimeout(resolve,1000));}
   throw new Error('Restart is taking longer than expected. Reload this page to check the controller.');
  }
  data=result;draft=structuredClone(data.values);lastSeen=Date.now();render();message(kind==='save'?'Saved. Apply these settings when the kiln is idle.':'Saved changes discarded.');
 }catch(error){failure(error.message||'Connection lost. Reload to check whether the change was saved.');}
 finally{busy=false;updateActions();}
}
async function load(){
 try{const response=await fetch('/api/settings',{cache:'no-store'});if(!response.ok)throw new Error('Cannot read controller settings.');data=await response.json();draft=structuredClone(data.values);lastSeen=Date.now();render();failure('');}catch(error){failure(error.message);$('status_title').textContent='Unable to load settings';$('status_detail').textContent='Check the connection and reload this page.';}
}
async function poll(){if(!data||busy)return;try{const response=await fetch('/api/settings',{cache:'no-store'});if(!response.ok)throw new Error();const next=await response.json();if(next.revision!==data.revision||next.token!==data.token){if(dirty()){failure('Settings changed in another session. Reload before saving; copy any unsaved values you want to keep.');data.can_apply=false;}else{data=next;draft=structuredClone(data.values);render();}}else{data.state=next.state;data.can_apply=next.can_apply;}lastSeen=Date.now();}catch(_){}updateActions();}
function closeReview(){$('settings_review').close();reviewAction=null;reviewSnapshot=null;}
$('review_cancel').onclick=$('review_close').onclick=closeReview;$('settings_review').addEventListener('cancel',()=>{reviewAction=null;});
$('review_confirm').onclick=()=>{const action=reviewAction,snapshot=reviewSnapshot;closeReview();if(action)mutate(action,snapshot);};
$('save_settings').onclick=()=>review('save');$('apply_settings').onclick=()=>review('apply');$('discard_settings').onclick=()=>{if(dirty()){draft=structuredClone(data.values);render();failure('');}else review('discard');};
$('settings_search').oninput=()=>{if(data)filter();};$('technical_names').onchange=e=>document.body.classList.toggle('show-technical',e.target.checked);
$('settings_form').onsubmit=e=>{e.preventDefault();if(dirty())review('save');};
$('export_settings').onclick=()=>{const blob=new Blob([JSON.stringify({version:1,values:draft},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='kiln-settings-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
addEventListener('beforeunload',e=>{if(dirty()){e.preventDefault();e.returnValue='';}});
load();setInterval(poll,5000);setInterval(updateActions,1000);
})();
