/* CoCan card. UI inspiration: KangCharge and CoCanBar (MIT); independently implemented for HA. */
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
class CocanCard extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:'open'}); this._entries=[]; this._busy=false; this._error=''; }
  static getStubConfig() { return {type:'custom:cocan-card'}; }
  static async getConfigElement() { return document.createElement('cocan-card-editor'); }
  setConfig(config) { this._config={...config}; this._signature=''; this.render(); }
  set hass(value) {
    this._hass=value;
    if (!this._loaded && !this._loading) this.load();
    this.render();
    if (this._history) this._history.hass=value;
  }
  getCardSize() { return 9; }
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
  text(key) { const entity=this.entity(key); return this.valid(entity) ? this._hass.formatEntityState(entity) : '—'; }
  async command(domain,service,data,confirmation) {
    if (this._busy) return;
    if (confirmation && !window.confirm(confirmation)) { this._signature=''; this.render(); return; }
    this._busy=true; this._error=''; this.render();
    try { await this._hass.callService(domain,service,data); }
    catch { this._error='操作失败，请检查连接；设备实际状态以刷新后的读数为准。'; }
    finally { this._busy=false; await this.load(); }
  }
  render() {
    if (!this._hass || !this._config) return;
    this._entry=this._entries.find(e=>e.entry_id===this._config.entry_id) || (!this._config.entry_id ? this._entries[0] : null);
    const entry=this._entry;
    const signature=JSON.stringify([entry,this._busy,this._error,this._port,Object.values(entry?.entities||{}).map(id=>this._hass.states[id])]);
    if (signature===this._signature) return;
    if (this.shadowRoot.activeElement?.matches('input')) return;
    this._signature=signature;
    const e=escapeHTML;
    const labels=['A','C1','C2','C3','C4'];
    const numeric=(key)=>{const entity=this.entity(key);return this.valid(entity) && Number.isFinite(Number(entity.state))?Number(entity.state):null;};
    const port=this._port || 1;
    const prefix=`port_${port}_`;
    const disabled=this._busy || !entry?.available;
    this.shadowRoot.innerHTML=`<style>
      :host{display:block;color:var(--primary-text-color)} *{box-sizing:border-box} ha-card{overflow:hidden;background:var(--ha-card-background,var(--card-background-color));border-radius:20px}
      .wrap{padding:20px;background:color-mix(in srgb,var(--primary-background-color) 85%,#f7b35b 15%)}
      header{display:flex;align-items:center;justify-content:space-between;gap:12px} h2{font-size:20px;margin:0} small,.muted{color:var(--secondary-text-color);font-size:12px}
      .total{font-size:42px;font-weight:650;margin:16px 0 4px;font-variant-numeric:tabular-nums}.summary{display:flex;justify-content:space-between;align-items:end}
      .panel{background:var(--card-background-color);border-radius:14px;padding:14px;margin-top:14px;border:1px solid var(--divider-color)}
      .ports{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:16px 0}.port{border:0;background:transparent;color:inherit;padding:0;min-width:0;cursor:pointer}.tube{height:100px;border:2px solid var(--divider-color);border-radius:30px;overflow:hidden;position:relative;background:repeating-linear-gradient(135deg,transparent 0 8px,color-mix(in srgb,var(--divider-color) 30%,transparent) 8px 10px)}
      .fill{position:absolute;bottom:0;width:100%;min-height:0;background:linear-gradient(#ffb15e,#ee7046);transition:height .35s}.port.selected .tube{border-color:#ee7046;box-shadow:0 0 0 2px #ee70462a}.port.off .tube{border-style:dashed}.port strong{display:block;margin:6px 0;font-size:14px}.power{font-size:12px;white-space:nowrap;font-variant-numeric:tabular-nums}.device{height:36px;border-radius:12px;background:var(--secondary-background-color);display:flex;align-items:center;justify-content:center;letter-spacing:3px;font-size:11px}
      .row{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:8px 0}.metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;font-size:13px}.metric{min-width:0;overflow-wrap:anywhere}.metric span{display:block;color:var(--secondary-text-color);font-size:11px;margin-bottom:4px}
      button.action{border:1px solid var(--divider-color);border-radius:9px;background:var(--card-background-color);color:var(--primary-text-color);padding:8px 12px;cursor:pointer;min-height:40px}button:disabled,select:disabled{opacity:.5;cursor:default} select{max-width:58%;min-height:40px;padding:6px;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);color:inherit;font:inherit} .error{color:var(--error-color);font-size:13px}.history{margin-top:12px}.status{font-size:12px;color:var(--secondary-text-color)}
      @media(prefers-reduced-motion:reduce){.fill{transition:none}} @media(max-width:380px){.wrap{padding:12px}.ports{gap:7px}.total{font-size:36px}.metrics{font-size:12px}}
    </style><ha-card><div class="wrap">
      <header><h2>${e(entry?.name || '小电拼')}</h2><button class="action" data-action="refresh" ${this._loading?'disabled':''} aria-label="刷新状态">刷新</button></header>
      ${this._entries.length>1?`<div class="row"><label for="device">设备</label><select id="device">${this._entries.map(x=>`<option value="${e(x.entry_id)}" ${x===entry?'selected':''}>${e(x.name)}</option>`).join('')}</select></div>`:''}
      ${!entry?'<p>请先添加小电拼集成，或在卡片配置中选择有效设备。</p>':`
      ${entry.source==='mqtt'?`<div class="row"><span>整机电源：${e(this.text('mqtt_device_power'))}</span><button class="action" data-action="device-power" ${disabled?'disabled':''}>切换电源</button><button class="action" data-action="reboot" ${disabled?'disabled':''}>重启</button></div><p class="muted">固件目标：${e(this.text('mqtt_firmware_target'))} · 详情和安装请在设备的更新实体中操作。</p>`:''}
      <div class="summary"><div><div class="total">${e(this.text('total_power'))}</div><small>总输出功率</small></div><span class="status">${entry.available?'在线':'离线'} · ${e(entry.model||'CoCan')}</span></div>
      <p class="muted">${({cloud:'云端读取',local:'局域网读取 · 云端控制暂不可用',local_cloud:'局域网读数 + 云端信息',mqtt:'本地 MQTT'})[entry.source]||'状态读取'}${entry.last_sample?' · '+e(new Date(entry.last_sample*1000).toLocaleTimeString()):''}</p>
      <div class="panel"><div class="ports">${labels.map((name,i)=>{const index=i+1,key=`port_${index}_`,watts=numeric(key+'power'),s=this.entity(key+'charging'),height=watts===null?0:Math.min(100,Math.sqrt(Math.max(0,watts)/(i?140:60))*100);return `<button class="port ${port===index?'selected':''} ${s?.state==='off'?'off':''}" data-port="${index}" aria-label="查看 ${name} 口详情" aria-pressed="${port===index}"><div class="tube"><div class="fill" style="height:${height}%"></div></div><strong>${name}</strong><span class="power">${e(watts===null?'—':watts.toFixed(1)+' W')}</span></button>`;}).join('')}</div><div class="device">CANDYSIGN · ${e(entry.model||'CoCan')}</div></div>
      <div class="panel"><div class="row"><strong>${labels[port-1]} 口</strong><div><button class="action" data-action="on" ${disabled||!this.entity(prefix+'charging')?'disabled':''}>开启</button> <button class="action" data-action="off" ${disabled||!this.entity(prefix+'charging')?'disabled':''}>关闭</button></div></div>
      <div class="metrics">${[['输出电压','voltage'],['输出电流','current'],['快充协议','protocol'],['温度状态','temp'],['本次电量','session_mwh'],['连接设备','pd_device'],['PD 工作电压','pd_op_v'],['PD 工作电流','pd_op_a'],['线缆','pd_cable'],['电池电量','pd_battery_pct']].map(([label,key])=>`<div class="metric"><span>${label}</span>${e(this.text(prefix+key))}</div>`).join('')}</div><p class="muted">端口开关状态来自充电状态，空闲不代表已经关闭；操作前请确认供电对象。</p></div>
      <div class="panel"><strong>充电与屏幕</strong>${['charging_strategy','temperature_mode','display_brightness','display_mode','idle_display'].map(key=>{const state=this.entity(key);if(!state)return '';const title=state.attributes.friendly_name?.replace(entry.name+' ','')||key;return `<div class="row"><label for="${key}">${e(title)}</label><select id="${key}" data-select="${e(state.entity_id)}" ${disabled||state.state==='unavailable'?'disabled':''}><option value="" disabled ${!this.valid(state)?'selected':''}>未读取</option>${(state.attributes.options||[]).map(value=>`<option value="${e(value)}" ${state.state===value?'selected':''}>${e(this._hass.formatEntityState({...state,state:value}))}</option>`).join('')}</select></div>`;}).join('')}<small>${entry.source==='mqtt'?'充电策略由 MQTT 读取。':'充电策略为上次设置值；MCP 无法读取当前策略。'}</small><div class="row"><span>整点报时</span><button class="action" data-action="chime" ${disabled||!this.entity('hourly_chime')?'disabled':''}>${this.entity('hourly_chime')?.state==='on'?'关闭报时':'开启报时'}</button></div></div>
      <div class="panel"><strong>临时功率分配</strong><p class="muted">填写全部端口，合计不超过 160 W；应用会让端口重新握手。</p><div class="ports">${labels.map((label,i)=>`<label class="metric">${label}<input style="width:100%;padding:8px;background:var(--card-background-color);color:inherit;border:1px solid var(--divider-color);border-radius:6px" data-watts="${i}" aria-label="${label} 口分配瓦数" type="number" min="0" max="${i?140:60}" step="1" placeholder="W" ${disabled?'disabled':''}></label>`).join('')}</div><button class="action" data-action="allocate" ${disabled?'disabled':''}>应用全部端口分配</button><small> 单口滑块需要先读取完整分配值；不会把未知端口当作 0 W。</small></div>
      <div class="row"><button class="action" data-action="history">最近 2 小时曲线</button><button class="action" data-action="details">设备全部实体</button></div><div class="history"></div>`}
      ${this._error?`<p class="error" role="alert">${e(this._error)}</p>`:''}
    </div></ha-card>`;
    this.shadowRoot.querySelectorAll('[data-port]').forEach(button=>button.onclick=()=>{this._port=Number(button.dataset.port);this.render();});
    this.shadowRoot.querySelector('[data-action="refresh"]').onclick=async()=>{if(this._entry){try{await this._hass.callWS({type:'mcp_cocan/refresh',entry_id:this._entry.entry_id});}catch{this._error='刷新失败，需管理员权限且设备在线。';}}await this.load();};
    this.shadowRoot.querySelector('#device')?.addEventListener('change',event=>{this._config.entry_id=event.target.value;this._history=null;this.render();});
    this.shadowRoot.querySelector('[data-action="device-power"]')?.addEventListener('click',()=>{const state=this.entity('mqtt_device_power');if(this.valid(state))this.command('switch',state.state==='on'?'turn_off':'turn_on',{entity_id:state.entity_id},'切换整机电源会中断供电，是否继续？');});
    this.shadowRoot.querySelector('[data-action="reboot"]')?.addEventListener('click',()=>{const state=this.entity('mqtt_reboot');if(state)this.command('button','press',{entity_id:state.entity_id},'设备即将重启并中断供电，是否继续？');});
    for (const action of ['on','off']) this.shadowRoot.querySelector(`[data-action="${action}"]`)?.addEventListener('click',()=>{const state=this.entity(prefix+'charging');if(state)this.command('switch','turn_'+action,{entity_id:state.entity_id},action==='off'?`关闭 ${labels[port-1]} 口将中断该端口供电，是否继续？`:null);});
    this.shadowRoot.querySelectorAll('[data-select]').forEach(select=>select.onchange=()=>this.command('select','select_option',{entity_id:select.dataset.select,option:select.value},select.id==='charging_strategy'?'切换充电策略可能导致端口重新握手，是否继续？':null));
    this.shadowRoot.querySelector('[data-action="chime"]')?.addEventListener('click',()=>{const state=this.entity('hourly_chime');if(state)this.command('switch',state.state==='on'?'turn_off':'turn_on',{entity_id:state.entity_id});});
    this.shadowRoot.querySelector('[data-action="allocate"]')?.addEventListener('click',async()=>{
      const inputs=[...this.shadowRoot.querySelectorAll('[data-watts]')];
      const watts=inputs.map(input=>input.value.trim()===''?NaN:Number(input.value));
      if(watts.some((value,i)=>!Number.isInteger(value)||value<0||value>(i?140:60))||watts.reduce((a,b)=>a+b,0)>160){this._error='请填写全部 5 个端口的整数功率，A 口≤60 W、其余≤140 W、合计≤160 W。';inputs.forEach(input=>input.blur());this.render();return;}
      if(!window.confirm(`应用 ${watts.join(' / ')} W，所有端口可能重新握手，是否继续？`))return;
      this._busy=true;this.render();
      try{await this._hass.callWS({type:'mcp_cocan/allocate',entry_id:entry.entry_id,watts});this._error='';}catch{this._error='功率分配失败，未确认生效。';}finally{this._busy=false;await this.load();}
    });
    this.shadowRoot.querySelector('[data-action="details"]')?.addEventListener('click',()=>{const first=Object.values(entry.entities).map(id=>this._hass.entities?.[id]).find(x=>x?.device_id);if(first){history.pushState(null,'',`/config/devices/device/${first.device_id}`);window.dispatchEvent(new Event('location-changed'));}});
    this.shadowRoot.querySelector('[data-action="history"]')?.addEventListener('click',async()=>{if(!this._history){const helpers=await window.loadCardHelpers();this._history=helpers.createCardElement({type:'history-graph',title:'输出功率',hours_to_show:2,entities:labels.map((_,i)=>entry.entities[`port_${i+1}_power`]).filter(Boolean)});this._history.hass=this._hass;}this.shadowRoot.querySelector('.history').replaceChildren(this._history);});
    if(this._history)this.shadowRoot.querySelector('.history')?.append(this._history);
  }
}
class CocanCardEditor extends HTMLElement {
  set hass(value){this._hass=value;this.draw();}
  setConfig(config){this._config=config;this.draw();}
  async draw(){if(!this._hass||!this._config||this._drawn)return;this._drawn=true;let entries;try{entries=await this._hass.callWS({type:'mcp_cocan/dashboard'});}catch{this._drawn=false;this.textContent='请先加载小电拼集成。';return;}const select=document.createElement('select');select.style.cssText='padding:12px;width:100%;font:inherit';select.setAttribute('aria-label','选择小电拼');for(const entry of entries){const option=document.createElement('option');option.value=entry.entry_id;option.textContent=entry.name;option.selected=entry.entry_id===this._config.entry_id;select.append(option);}select.onchange=()=>{this._config={...this._config,entry_id:select.value};this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:this._config},bubbles:true,composed:true}));};this.replaceChildren(select);}
}
if(!customElements.get('cocan-card'))customElements.define('cocan-card',CocanCard);
if(!customElements.get('cocan-card-editor'))customElements.define('cocan-card-editor',CocanCardEditor);
window.customCards=window.customCards||[];
if(!window.customCards.some(x=>x.type==='cocan-card'))window.customCards.push({type:'cocan-card',name:'小电拼控制面板',description:'端口功率图、设备详情、模式与屏幕控制、充电曲线'});
