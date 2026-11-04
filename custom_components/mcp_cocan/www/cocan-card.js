/* HA cards independently implemented from KangCharge / CoCanBar UI references.
 * Attribution and MIT licenses: bundled REFERENCES.md and licenses/.
 */
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const portLabels = ['A','C1','C2','C3','C4'];
class CocanCard extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:'open'}); this._entries=[]; this._busy=false; this._error=''; }
  static getStubConfig() { return {type:'custom:cocan-card'}; }
  static async getConfigElement() { return document.createElement('cocan-card-editor'); }
  setConfig(config) { this._config={...config,size:['compact','regular','large'].includes(config.size)?config.size:'regular',max_width:Number.isFinite(Number(config.max_width))?Math.min(1200,Math.max(260,Number(config.max_width))):560}; this._signature=''; this.render(); }
  set hass(value) {
    this._hass=value;
    if (!this._loaded && !this._loading) this.load();
    this.render();
    if (this._history) this._history.hass=value;
  }
  getCardSize() { return this.view==='full'?12:this.view==='ports'?8:5; }
  getGridOptions() { return {columns:12,rows:'auto',min_columns:6}; }
  get view() { return 'full'; }
  connectedCallback() { this._timer=setInterval(()=>this.load(),15000); }
  disconnectedCallback() { clearInterval(this._timer); }
  async load() {
    if (!this._hass || this._loading) return;
    this._loading=true;
    try { this._entries=await this._hass.callWS({type:'mcp_cocan/dashboard'}); this._loaded=true; }
    catch { this._error='无法读取小电拼，请确认集成已加载。'; }
    finally { this._loading=false; this.render(); }
  }
  entity(key) { const id=this._entry?.entities[key]; return id ? this._hass.states[id] : null; }
  valid(entity) { return entity && !['unknown','unavailable'].includes(entity.state); }
  text(key) { const entity=this.entity(key); return this._entry?.available && this.valid(entity) ? this._hass.formatEntityState(entity) : '—'; }
  number(key) { const state=this.entity(key);return this._entry?.available&&this.valid(state)&&Number.isFinite(Number(state.state))?Number(state.state):null; }
  async command(domain,service,data,confirmation) {
    if (this._busy) return;
    if (confirmation && !window.confirm(confirmation)) return;
    this._busy=true; this._error=''; this.render();
    try { await this._hass.callService(domain,service,data); }
    catch { this._error='操作失败，请检查连接；设备实际状态以刷新后的读数为准。'; }
    finally { this._busy=false; await this.load(); }
  }
  diagram() {
    const e=escapeHTML;
    return `<div class="diagram" role="group" aria-label="五口功率与充电器连线图">
      <svg viewBox="0 0 500 280" aria-hidden="true" focusable="false">
        <defs><linearGradient id="body" x2="0" y2="1"><stop stop-color="#fffcf4"/><stop offset="1" stop-color="#e7dfcf"/></linearGradient><filter id="shadow" x="-20%" y="-30%" width="140%" height="170%"><feDropShadow dx="0" dy="6" stdDeviation="5" flood-color="#48351b" flood-opacity=".16"/></filter></defs>
        <rect class="charger-body" x="204" y="174" width="284" height="100" rx="22" filter="url(#shadow)"/>
        ${portLabels.map((_,i)=>{const active=this._entry.available&&(this.number(`port_${i+1}_power`)||0)>0;return `<path class="cable ${active?'active':''}" d="M ${50+i*100} 76 C ${50+i*100} 152, ${242+i*47} 121, ${242+i*47} 198"/>`;}).join('')}
        ${portLabels.map((_,i)=>`<rect class="socket" x="${232+i*47}" y="190" width="${i?20:26}" height="12" rx="${i?6:2}"/>`).join('')}
        <rect class="screen" x="229" y="226" width="74" height="30" rx="6"/>
        <text class="screen-value" x="266" y="246" text-anchor="middle">${e(this.number('total_power')===null?'—':this.number('total_power').toFixed(1)+' W')}</text>
        <text class="brand" x="388" y="247" text-anchor="middle">CANDYSIGN</text>
      </svg>
      <div class="chips">${portLabels.map((label,i)=>{const index=i+1,watts=this.number(`port_${index}_power`),active=this._entry.available&&watts!==null&&watts>0;return `<button class="chip ${active?'active':''} ${this._port===index?'selected':''}" data-port="${index}" aria-pressed="${this._port===index}" aria-label="查看 ${label} 口详情"><strong>${label==='A'?'USB-A':label}</strong><span class="chip-value">${e(watts===null?'—':watts.toFixed(1))}<small>${watts===null?'':' W'}</small></span><span class="chip-protocol">${e(this.text(`port_${index}_protocol`))}</span></button>`;}).join('')}</div>
    </div>`;
  }
  portList() {
    const e=escapeHTML;
    return `<div class="port-list" role="group" aria-label="端口状态列表">${portLabels.map((label,i)=>{const index=i+1,key=`port_${index}_`,watts=this.number(key+'power'),active=this._entry.available&&watts!==null&&watts>0;return `<button class="port-row ${active?'active':''} ${this._port===index?'selected':''}" data-port="${index}" aria-pressed="${this._port===index}"><span class="port-tag">${label}</span><span class="port-copy"><strong>${e(this.text(key+'pd_device')==='—'?(active?'正在供电':watts===null?'未读取':'空闲'):this.text(key+'pd_device'))}</strong><small>${e(this.text(key+'protocol'))} · ${e(this.text(key+'voltage'))} · ${e(this.text(key+'current'))}</small></span><span class="row-watts">${e(watts===null?'—':watts.toFixed(1))}<small>${watts===null?'':' W'}</small></span><span aria-hidden="true">›</span></button>`;}).join('')}</div>`;
  }
  render() {
    if (!this._hass || !this._config) return;
    this._entry=this._entries.find(x=>x.entry_id===this._config.entry_id) || (!this._config.entry_id ? this._entries[0] : null);
    const entry=this._entry;
    const signature=JSON.stringify([entry,this._hass.themes?.darkMode,this._config,this._busy,this._error,this._port,Object.values(entry?.entities||{}).map(id=>this._hass.states[id])]);
    if (signature===this._signature || this.shadowRoot.activeElement?.matches('input')) return;
    this._signature=signature;
    const e=escapeHTML,port=this._port||1,prefix=`port_${port}_`,disabled=this._busy||!entry?.available||entry?.control_available===false;
    const full=this.view==='full',details=this.view==='ports'||(this.view==='power'&&this._port);
    const compact=this._config.size==='compact',large=this._config.size==='large';
    this.shadowRoot.innerHTML=`<style>
      :host{display:block;max-width:${this._config.max_width}px;margin-inline:auto;--accent:var(--cocan-accent,#e9812b);--canvas:var(--ha-card-background,var(--card-background-color,#fff));--surface:var(--ha-card-background,var(--card-background-color,#fff));--line:var(--divider-color,#e4e4e4);--ink:var(--primary-text-color,#242424);--muted:var(--secondary-text-color,#777);color:var(--ink)}*{box-sizing:border-box}ha-card{display:block;overflow:hidden;border-radius:20px;background:var(--canvas);color:var(--ink);border:1px solid var(--line)}button,select,input{font:inherit}button{color:inherit;cursor:pointer}button:disabled,select:disabled,input:disabled{opacity:.45;cursor:default}button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:3px}.wrap{padding:${compact?12:large?24:18}px}header,.row,.summary,.footer{display:flex;align-items:center;justify-content:space-between;gap:10px}header{margin-bottom:16px}.heading{min-width:0}.eyebrow{color:var(--accent);font-size:10px;letter-spacing:2px;font-weight:800}h2{font-size:19px;margin:4px 0;overflow-wrap:anywhere}small,.muted{font-size:11px;color:var(--muted)}.muted{line-height:1.6}.badge{display:inline-block;font-size:10px;padding:3px 7px;border-radius:6px;background:${entry?.available?'#51836020':'#9c8b7820'};color:${entry?.available?'#598064':'var(--muted)'}}.summary{align-items:end}.total{font-size:42px;font-weight:750;line-height:1.15;font-variant-numeric:tabular-nums;letter-spacing:-1.5px}.total-label{font-size:11px;color:var(--muted);margin:5px 0}.strategy{max-width:42%;text-align:right;font-size:12px}.panel{padding:14px;margin-top:14px;border:1px solid var(--line);border-radius:14px;background:var(--surface)}.row{margin:10px 0;flex-wrap:wrap}.action{min-height:36px;border:1px solid var(--line);border-radius:9px;background:var(--surface);padding:7px 10px;font-size:12px}.toolbar{display:flex;gap:6px;flex-shrink:0}.toolbar .action{padding:7px 9px}select{max-width:58%;min-height:36px;padding:6px;background:var(--surface);color:inherit;border:1px solid var(--line);border-radius:8px}.diagram{position:relative;container-type:inline-size;aspect-ratio:500/280;margin:18px auto 0;max-width:${compact?420:large?680:500}px}.diagram svg{width:100%;height:100%;display:block}.charger-body{fill:url(#body);stroke:#d9d0bd;stroke-width:1.5}.cable{fill:none;stroke:var(--line);stroke-width:5;stroke-linecap:round}.cable.active{stroke:var(--accent)}.socket,.screen{fill:#2d2923}.screen-value{fill:#f4ad50;font:700 15px sans-serif}.brand{fill:var(--muted);font:700 12px sans-serif;letter-spacing:3px}.chips{position:absolute;inset:0 0 auto;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:2cqi}.chip{min-width:0;border:1.5px solid var(--line);border-radius:9px;background:var(--surface);padding:1cqi .6cqi;overflow:hidden;text-align:center}.chip.active{border-color:var(--accent)}.chip.selected{box-shadow:0 0 0 2px #e9812b35}.chip strong{display:block;font-size:clamp(9px,2.5cqi,13px);line-height:1.7}.chip-value{display:block;font-size:clamp(16px,5cqi,26px);line-height:1.4;font-weight:750;font-variant-numeric:tabular-nums;white-space:nowrap}.chip.active .chip-value{color:var(--accent)}.chip-value small{font-size:9px}.chip-protocol{display:block;border-top:1px solid var(--line);font-size:clamp(8px,2.2cqi,11px);line-height:1.8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted)}.port-list{margin-top:14px;border:1px solid var(--line);border-radius:14px;background:var(--surface);overflow:hidden}.port-row{display:flex;align-items:center;gap:10px;width:100%;min-height:${compact?54:large?76:64}px;padding:${compact?9:large?16:12}px;border:0;border-bottom:1px solid var(--line);background:transparent;text-align:left}.port-row:last-child{border-bottom:0}.port-row.selected{background:#e9812b0c}.port-tag{display:grid;place-items:center;width:36px;height:30px;border-radius:7px;background:var(--canvas);font-size:12px;font-weight:800;color:var(--muted);flex-shrink:0}.port-row.active .port-tag{background:#e9812b18;color:var(--accent)}.port-copy{min-width:0;flex:1}.port-copy strong,.port-copy small{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.port-copy strong{font-size:12px;margin-bottom:5px}.row-watts{font-size:20px;font-weight:750;white-space:nowrap;font-variant-numeric:tabular-nums}.row-watts small{font-size:10px}.metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;font-size:13px}.metric{min-width:0;overflow-wrap:anywhere}.metric span{display:block;font-size:10px;color:var(--muted);margin-bottom:5px}.allocations{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}.allocations input{width:100%;padding:8px 4px;background:var(--surface);color:inherit;border:1px solid var(--line);border-radius:6px}.footer{margin-top:14px;flex-wrap:wrap}.history{margin-top:12px}.error{color:var(--error-color,#b44b33);font-size:12px}a{color:var(--accent)}
      @media(max-width:380px){.wrap{padding:12px}.chips{gap:6px}.total{font-size:36px}.port-row{padding:10px;gap:8px}.toolbar{gap:4px}}
    </style><ha-card><div class="wrap">
      <header><div class="heading"><span class="eyebrow">COCAN MIRROR</span><h2>${e(this._config.title||entry?.name||'小电拼')}</h2><span class="badge">${entry?(entry.available?'在线':'离线'):'未配置'}</span> <small>${e(entry?.model||'')}</small></div><div class="toolbar"><button class="action" data-action="settings" aria-label="连接设置">设置</button><button class="action" data-action="refresh" ${this._loading?'disabled':''} aria-label="刷新状态">刷新</button></div></header>
      ${this._entries.length>1?`<div class="row"><label for="device">设备</label><select id="device">${this._entries.map(x=>`<option value="${e(x.entry_id)}" ${x===entry?'selected':''}>${e(x.name)}</option>`).join('')}</select></div>`:''}
      ${!entry?'<p>请先添加小电拼集成，或在卡片配置中选择设备。</p>':`
        <div class="summary"><div><div class="total">${e(this.text('total_power'))}</div><div class="total-label">总输出功率</div></div><div class="strategy">${e(this.text('charging_strategy'))}<br><small>充电策略</small></div></div>
        ${this.view==='ports'?this.portList():this.diagram()}
        ${full||details?`<div class="panel"><div class="row"><strong>${portLabels[port-1]} 口详情</strong><div><button class="action" data-action="on" ${disabled||!this.entity(prefix+'charging')?'disabled':''}>开启</button> <button class="action" data-action="off" ${disabled||!this.entity(prefix+'charging')?'disabled':''}>关闭</button></div></div><div class="metrics">${[['输出电压','voltage'],['输出电流','current'],['快充协议','protocol'],['温度状态','temp'],['本次电量','session_mwh'],['连接设备','pd_device'],['PD 工作电压','pd_op_v'],['PD 工作电流','pd_op_a'],['线缆','pd_cable'],['电池电量','pd_battery_pct']].map(([label,key])=>`<div class="metric"><span>${label}</span>${e(this.text(prefix+key))}</div>`).join('')}</div><p class="muted">空闲不代表端口已关闭。</p></div>`:''}
        ${full?`
          ${(entry.connection_mode||entry.source)==='mqtt'?`<div class="panel row"><span>整机电源：${e(this.text('mqtt_device_power'))}</span><button class="action" data-action="device-power" ${disabled?'disabled':''}>切换电源</button><button class="action" data-action="reboot" ${disabled?'disabled':''}>重启</button></div>`:''}
          <div class="panel"><strong>充电与屏幕</strong>${['charging_strategy','temperature_mode','display_brightness','display_mode','idle_display'].map(key=>{const state=this.entity(key);if(!state)return '';const title=state.attributes.friendly_name?.replace(entry.name+' ','')||key;return `<div class="row"><label for="${key}">${e(title)}</label><select id="${key}" data-select="${e(state.entity_id)}" ${disabled||state.state==='unavailable'?'disabled':''}><option value="" disabled ${!this.valid(state)?'selected':''}>未读取</option>${(state.attributes.options||[]).map(value=>`<option value="${e(value)}" ${state.state===value?'selected':''}>${e(this._hass.formatEntityState({...state,state:value}))}</option>`).join('')}</select></div>`;}).join('')}<small>${(entry.connection_mode||entry.source)==='mqtt'?'充电策略由设备读取。':'充电策略为上次设置值。'}</small><div class="row"><span>整点报时</span><button class="action" data-action="chime" ${disabled||!this.entity('hourly_chime')?'disabled':''}>${this.entity('hourly_chime')?.state==='on'?'关闭报时':'开启报时'}</button></div></div>
          <div class="panel"><strong>临时功率分配</strong><p class="muted">合计不超过 160 W，应用后端口将重新握手。</p><div class="allocations">${portLabels.map((label,i)=>`<label class="metric">${label}<input data-watts="${i}" aria-label="${label} 口分配瓦数" type="number" min="0" max="${i?140:60}" step="1" placeholder="W" ${disabled?'disabled':''}></label>`).join('')}</div><div class="row"><button class="action" data-action="allocate" ${disabled?'disabled':''}>应用全部端口分配</button></div></div>
        `:''}
        <div class="footer"><small>${(entry.connection_mode||entry.source)==='mqtt'?'本地 MQTT':'官方云'}${entry.last_sample?' · '+e(new Date(entry.last_sample*1000).toLocaleTimeString()):''}</small><div><button class="action" data-action="history">功率曲线</button> <button class="action" data-action="details">设备详情</button></div></div><div class="history"></div>
      `}
      ${this._error?`<p class="error" role="alert">${e(this._error)}</p>`:''}
    </div></ha-card>`;
    this.bindActions(disabled,prefix,port);
    if(this._history)this.shadowRoot.querySelector('.history')?.append(this._history);
  }
  bindActions(disabled,prefix,port) {
    const entry=this._entry;
    this.shadowRoot.querySelectorAll('[data-port]').forEach(button=>button.onclick=()=>{this._port=Number(button.dataset.port);this.render();});
    this.shadowRoot.querySelector('[data-action="settings"]').onclick=()=>this.dispatchEvent(new CustomEvent('show-dialog',{bubbles:true,composed:true,detail:{dialogTag:'cocan-settings-dialog',dialogImport:()=>import('/mcp_cocan/broker-settings.js?v=0.4.1b17'),dialogParams:{entry_id:entry?.entry_id}}}));
    this.shadowRoot.querySelector('[data-action="refresh"]').onclick=async()=>{if(entry){try{await this._hass.callWS({type:'mcp_cocan/refresh',entry_id:entry.entry_id});}catch{this._error='刷新失败，需管理员权限且设备在线。';}}await this.load();};
    this.shadowRoot.querySelector('#device')?.addEventListener('change',event=>{this._config.entry_id=event.target.value;this._port=null;this._history=null;this.render();});
    this.shadowRoot.querySelector('[data-action="device-power"]')?.addEventListener('click',()=>{const state=this.entity('mqtt_device_power');if(this.valid(state))this.command('switch',state.state==='on'?'turn_off':'turn_on',{entity_id:state.entity_id},'切换整机电源会中断供电，是否继续？');});
    this.shadowRoot.querySelector('[data-action="reboot"]')?.addEventListener('click',()=>{const state=this.entity('mqtt_reboot');if(state)this.command('button','press',{entity_id:state.entity_id},'设备即将重启并中断供电，是否继续？');});
    for(const action of ['on','off'])this.shadowRoot.querySelector(`[data-action="${action}"]`)?.addEventListener('click',()=>{const state=this.entity(prefix+'charging');if(state&&!disabled)this.command('switch','turn_'+action,{entity_id:state.entity_id},action==='off'?`关闭 ${portLabels[port-1]} 口将中断该端口供电，是否继续？`:null);});
    this.shadowRoot.querySelectorAll('[data-select]').forEach(select=>select.onchange=()=>this.command('select','select_option',{entity_id:select.dataset.select,option:select.value},select.id==='charging_strategy'?'切换充电策略可能导致端口重新握手，是否继续？':null));
    this.shadowRoot.querySelector('[data-action="chime"]')?.addEventListener('click',()=>{const state=this.entity('hourly_chime');if(state)this.command('switch',state.state==='on'?'turn_off':'turn_on',{entity_id:state.entity_id});});
    this.shadowRoot.querySelector('[data-action="allocate"]')?.addEventListener('click',async()=>{
      const inputs=[...this.shadowRoot.querySelectorAll('[data-watts]')],watts=inputs.map(input=>input.value.trim()===''?NaN:Number(input.value));
      if(watts.some((value,i)=>!Number.isInteger(value)||value<0||value>(i?140:60))||watts.reduce((a,b)=>a+b,0)>160){this._error='请填写全部 5 个端口的整数功率，A 口≤60 W、其余≤140 W、合计≤160 W。';inputs.forEach(input=>input.blur());this.render();return;}
      if(!window.confirm(`应用 ${watts.join(' / ')} W，所有端口可能重新握手，是否继续？`))return;
      this._busy=true;this.render();
      try{await this._hass.callWS({type:'mcp_cocan/allocate',entry_id:entry.entry_id,watts});this._error='';}catch{this._error='功率分配失败，未确认生效。';}finally{this._busy=false;await this.load();}
    });
    this.shadowRoot.querySelector('[data-action="details"]')?.addEventListener('click',()=>{const first=Object.values(entry.entities).map(id=>this._hass.entities?.[id]).find(x=>x?.device_id);if(first){history.pushState(null,'',`/config/devices/device/${first.device_id}`);window.dispatchEvent(new Event('location-changed'));}});
    this.shadowRoot.querySelector('[data-action="history"]')?.addEventListener('click',async()=>{try{if(!this._history){const helpers=await window.loadCardHelpers();this._history=helpers.createCardElement({type:'history-graph',title:'输出功率 · 最近 2 小时',hours_to_show:2,entities:portLabels.map((_,i)=>entry.entities[`port_${i+1}_power`]).filter(Boolean)});this._history.hass=this._hass;}this.shadowRoot.querySelector('.history').replaceChildren(this._history);}catch{this._error='暂时无法加载功率曲线。';this.render();}});
  }
}
class CocanPowerCard extends CocanCard {
  get view() { return 'power'; }
  static getStubConfig() { return {type:'custom:cocan-power-card'}; }
}
class CocanPortsCard extends CocanCard {
  get view() { return 'ports'; }
  static getStubConfig() { return {type:'custom:cocan-ports-card'}; }
}
class CocanCardEditor extends HTMLElement {
  set hass(value){this._hass=value;this.draw();}
  setConfig(config){this._config={...config};this._drawn=false;this.draw();}
  async draw(){
    if(!this._hass||!this._config||this._drawn)return;
    this._drawn=true;let entries;
    try{entries=await this._hass.callWS({type:'mcp_cocan/dashboard'});}catch{this._drawn=false;this.textContent='请先加载小电拼集成。';return;}
    const select=document.createElement('select');select.style.cssText='padding:12px;width:100%;font:inherit';select.setAttribute('aria-label','选择小电拼');
    const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='自动选择第一台设备';placeholder.selected=!this._config.entry_id;select.append(placeholder);
    for(const entry of entries){const option=document.createElement('option');option.value=entry.entry_id;option.textContent=entry.name;option.selected=entry.entry_id===this._config.entry_id;select.append(option);}
    select.onchange=()=>{this._config={...this._config,entry_id:select.value||undefined};this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this._config},bubbles:true,composed:true}));};const field=(label,control)=>{const wrap=document.createElement('label');wrap.style.cssText='display:grid;gap:8px;margin:12px 0;font:inherit';const text=document.createElement('span');text.textContent=label;wrap.append(text,control);return wrap;};
    const emit=()=>this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:{...this._config}},bubbles:true,composed:true}));
    const size=document.createElement('select');size.style.cssText=select.style.cssText;size.setAttribute('aria-label','卡片尺寸');
    for(const [value,label] of [['compact','紧凑'],['regular','标准'],['large','宽松']]){const option=document.createElement('option');option.value=value;option.textContent=label;option.selected=(this._config.size||'regular')===value;size.append(option);}
    size.onchange=()=>{this._config.size=size.value;emit();};
    const width=document.createElement('input');width.type='number';width.min='260';width.max='1200';width.step='10';width.value=this._config.max_width||560;width.setAttribute('aria-label','最大宽度（像素）');width.style.cssText=select.style.cssText;
    width.onchange=()=>{const value=Number(width.value);if(Number.isFinite(value)&&value>=260&&value<=1200){this._config.max_width=value;emit();}};
    const hint=document.createElement('small');hint.textContent='最大宽度受仪表盘列宽限制；Sections 布局可在卡片的“布局”页拖动宽高。';
    this.replaceChildren(field('设备',select),field('卡片尺寸',size),field('最大宽度（像素）',width),hint);
  }
}
for(const [name,component] of [['cocan-card',CocanCard],['cocan-power-card',CocanPowerCard],['cocan-ports-card',CocanPortsCard],['cocan-card-editor',CocanCardEditor]])if(!customElements.get(name))customElements.define(name,component);
window.customCards=window.customCards||[];
for(const item of [
  {type:'cocan-power-card',name:'小电拼 · 功率概览',description:'KangCharge 风格五口连线图、充电器机身与实时功率',preview:true},
  {type:'cocan-ports-card',name:'小电拼 · 端口详情',description:'CoCanBar 风格端口列表、电压电流、PD 与端口开关',preview:true},
  {type:'cocan-card',name:'小电拼 · 完整控制',description:'功率图、模式与屏幕控制、临时分配与充电曲线',preview:true}
])if(!window.customCards.some(x=>x.type===item.type))window.customCards.push(item);
