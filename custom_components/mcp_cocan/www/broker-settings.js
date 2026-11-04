/* Unified Broker settings. All writes use the server's confirmed options flow. */
const brokerEscape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const brokerErrors = {
  device_broker_unavailable:'无法读取设备当前 Broker，请检查设备局域网地址和连接。',
  broker_detection_failed:'目标地址必须与 HA MQTT 集成的 Broker 一致，请检查 HA MQTT 配置。',
  broker_source_changed:'设备连接已变化，请核对更新后的来源和目标，再次确认。',
  device_broker_switch_failed:'设备切换未完成，请刷新当前连接后重试。',
  broker_connect_pending:'设备已选择目标 Broker，目标服务尚未就绪，请稍后重新确认。',
  official_mcp_required:'请先在集成的当前连接参数中填写官方 MCP 地址。',
  wrong_device:'设备序列号不匹配，未保存 HA 接入设置。',
  confirmation_required:'请先预览并确认切换。'
};
class CocanBrokerSettings extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this._entries=[];this._target='official';this._custom='';this._busy=false;this._generation=0;}
  set hass(value){this._hass=value;if(!this._started){this._started=true;this.initialize();}}
  connectedCallback(){this.render();}
  disconnectedCallback(){this.invalidate();}
  async api(args){return this._hass.callWS({type:'mcp_cocan/broker_settings',entry_id:this._entryId,...args});}
  message(error){return brokerErrors[error]||'操作未完成，请检查连接后重试。';}
  async initialize(){
    this._busy=true;this.render();
    try{
      this._entries=await this._hass.callWS({type:'mcp_cocan/dashboard'});
      const requested=this.entryId||new URLSearchParams(location.search).get('entry_id');
      this._entryId=this._entries.find(x=>x.entry_id===requested)?.entry_id||this._entries[0]?.entry_id;
      if(this._entryId)await this.status(true);else this._error='请先添加小电拼集成。';
    }catch{this._error='无法加载设备设置。';}finally{this._busy=false;this.render();}
  }
  async invalidate(){
    this._generation++;const id=this._preview?.flow_id;this._preview=null;this._checked=false;
    if(id&&this._hass)try{await this.api({action:'cancel',flow_id:id});}catch{}
  }
  async status(initial=false){
    this._status=await this.api({action:'status'});
    if(initial){this._custom=this._status.custom||'';this._target=this._status.current===this._status.official?'official':'custom';}
    if(this._status.error)this._error=this.message(this._status.error);
  }
  async select(target){await this.invalidate();this._target=target;this._error='';this._success='';this.render();}
  async prepare(){
    if(this._busy)return;await this.invalidate();const generation=this._generation;
    this._busy=true;this._error='';this._success='';this.render();
    try{
      const result=await this.api({action:'prepare',target:this._target,...(this._target==='custom'?{broker_url:this._custom.trim()}:{})});
      if(generation!==this._generation){if(result.flow_id)await this.api({action:'cancel',flow_id:result.flow_id});return;}
      this._preview=result;const error=Object.values(result.errors||{})[0];if(error)this._error=this.message(error);
    }catch(e){this._error=this.message(e.code);}finally{this._busy=false;this.render();}
  }
  async apply(){
    if(this._busy||!this._checked||!this._preview?.flow_id)return;
    this._busy=true;this._error='';this.render();
    try{
      const result=await this.api({action:'confirm',flow_id:this._preview.flow_id,confirm:true});
      this._checked=false;
      if(result.completed){this._preview=null;this._success='切换成功，设备与 Home Assistant 已连接到目标服务。';await this.status();}
      else{this._preview=result;this._error=this.message(Object.values(result.errors||{})[0]);}
    }catch(e){this._checked=false;this._preview=null;this._error=this.message(e.code);}
    finally{this._busy=false;this.render();}
  }
  render(){
    const e=brokerEscape,busy=this._busy?'disabled':'',s=this._status,p=this._preview?.preview;
    this.shadowRoot.innerHTML=`<style>
      :host{display:block;height:100%;overflow:auto;background:var(--primary-background-color);color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family, sans-serif)}*{box-sizing:border-box}header{display:flex;align-items:center;gap:14px;padding:12px 20px;border-bottom:1px solid var(--divider-color);background:var(--card-background-color)}h1{font-size:20px;margin:0}main{max-width:960px;margin:32px auto;padding:0 24px 40px}h2{margin:0 0 8px;font-size:26px}p{color:var(--secondary-text-color);line-height:1.6}.surface{border:1px solid var(--divider-color);background:var(--card-background-color);border-radius:16px;padding:24px;margin-top:20px}.row{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap}.label{font-size:13px;color:var(--secondary-text-color);margin-bottom:8px}.address{font-size:16px;overflow-wrap:anywhere}.mode{font-size:12px;color:var(--primary-color)}.tabs{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:22px 0}.tab{text-align:left;padding:18px;border:1px solid var(--divider-color);border-radius:12px;background:var(--card-background-color);color:inherit;font:inherit;cursor:pointer}.tab[aria-pressed=true]{border:2px solid var(--primary-color);padding:17px;background:var(--secondary-background-color)}.tab strong,.tab small{display:block}.tab small{margin-top:8px;color:var(--secondary-text-color)}button{font:inherit;cursor:pointer}button:disabled{opacity:.5;cursor:default}.action{border:1px solid var(--divider-color);border-radius:9px;padding:10px 16px;color:var(--primary-text-color);background:var(--card-background-color)}.primary{background:var(--primary-color);color:var(--text-primary-color,#fff);border:0}.field{display:grid;gap:10px;margin-top:18px}input[type=url],select{width:100%;padding:13px;border:1px solid var(--divider-color);border-radius:8px;font:inherit;color:inherit;background:var(--card-background-color)}.confirm{border-color:var(--primary-color)}.route{display:grid;grid-template-columns:1fr 32px 1fr;gap:14px;align-items:center;margin:22px 0}.arrow{text-align:center;font-size:24px;color:var(--primary-color)}.check{display:flex;align-items:flex-start;gap:10px;margin:24px 0;line-height:1.5}.check input{width:18px;height:18px}.error{color:var(--error-color);padding:12px 0}.success{color:var(--success-color,#27844c);padding:12px 0}.actions{display:flex;gap:12px;justify-content:flex-end;margin-top:24px}a{color:var(--primary-color)}@media(max-width:600px){main{margin:20px auto;padding:0 14px 24px}.surface{padding:18px}.route{grid-template-columns:1fr}.arrow{transform:rotate(90deg)}.tabs{gap:8px}.tab{padding:14px}.tab[aria-pressed=true]{padding:13px}}
    </style>${this.embedded?'':'<header><h1>小电拼设置</h1></header>'}<main>
    <div class="row"><div><h2>MQTT Broker</h2><p>选择连接服务，在此页面核对并确认切换。</p></div>${this._entries.length>1?`<select id="device" aria-label="设备">${this._entries.map(x=>`<option value="${e(x.entry_id)}" ${x.entry_id===this._entryId?'selected':''}>${e(x.name)}</option>`).join('')}</select>`:''}</div>
    <section class="surface"><div class="row"><div><div class="label">${e(s?.name||'设备')} · 当前连接</div><div class="address">${e(s?.current||'正在读取…')}</div><span class="mode">Home Assistant · ${s?.mode==='mqtt'?'MQTT':'MCP'}</span></div><button class="action" id="refresh" ${busy}>刷新</button></div></section>
    <section class="surface"><div class="row"><strong>目标连接</strong><button class="action" id="quick" ${busy||!s?.current?'disabled':''}>切换到${s?.current===s?.official?'自定义':'官方'}</button></div>
    <div class="tabs" role="group" aria-label="Broker 类型"><button class="tab" data-target="official" aria-pressed="${this._target==='official'}" ${busy}><strong>官方 Broker</strong><small>使用官方服务，通过 MCP 接入</small></button><button class="tab" data-target="custom" aria-pressed="${this._target==='custom'}" ${busy}><strong>自定义 Broker</strong><small>默认使用 Home Assistant 的 MQTT</small></button></div>
    ${this._target==='custom'?`<label class="field">Broker 地址<input id="broker" type="url" spellcheck="false" value="${e(this._custom)}" placeholder="mqtt://host:1883" ${busy}></label><p>与 HA MQTT 集成使用同一个 Broker。</p>`:`<div class="label">官方地址</div><div class="address">${e(s?.official||'—')}</div>`}
    <div class="actions"><button class="action primary" id="prepare" ${busy||!s?.current?'disabled':''}>${this._busy?'处理中…':'预览切换'}</button></div></section>
    ${p?`<section class="surface confirm"><strong>确认本次切换</strong><div class="route"><div><div class="label">当前 · ${e(p.from_mode)}</div><div class="address">${e(p.from_broker)}</div></div><div class="arrow">→</div><div><div class="label">目标 · ${e(p.to_mode)}</div><div class="address">${e(p.to_broker)}</div></div></div><label class="check"><input id="confirm" type="checkbox" ${this._checked?'checked':''} ${busy}>我已核对来源和目标，确认切换设备与 Home Assistant。</label><div class="actions"><button class="action" id="cancel" ${busy}>取消</button><button class="action primary" id="apply" ${busy||!this._checked||Object.keys(this._preview.errors||{}).length?'disabled':''}>${this._busy?'正在切换…':'确认并切换'}</button></div></section>`:''}
    ${this._error?`<div class="error" role="alert">${e(this._error)}</div>`:''}${this._success?`<div class="success" role="status">${e(this._success)}</div>`:''}
    ${this.advancedAvailable?`<p><button class="action" id="advanced" ${busy}>连接参数与实体管理</button></p>`:''}</main>`;
    this.shadowRoot.querySelector('#advanced')?.addEventListener('click',()=>this.dispatchEvent(new CustomEvent('cocan-advanced-settings',{bubbles:true,composed:true,detail:{entry_id:this._entryId}})));
    this.shadowRoot.querySelectorAll('[data-target]').forEach(x=>x.onclick=()=>this.select(x.dataset.target));
    this.shadowRoot.querySelector('#broker')?.addEventListener('input',event=>{this._custom=event.target.value;this.invalidate();this._error='';this._success='';this.shadowRoot.querySelector('.confirm')?.remove();});
    this.shadowRoot.querySelector('#prepare').onclick=()=>this.prepare();
    this.shadowRoot.querySelector('#quick').onclick=async()=>{await this.select(s?.current===s?.official?'custom':'official');await this.prepare();};
    this.shadowRoot.querySelector('#refresh').onclick=async()=>{if(this._busy)return;await this.invalidate();this._busy=true;this._error='';this.render();try{await this.status();}catch{this._error='刷新失败，请稍后重试。';}finally{this._busy=false;this.render();}};
    this.shadowRoot.querySelector('#confirm')?.addEventListener('change',event=>{this._checked=event.target.checked;this.shadowRoot.querySelector('#apply').disabled=!this._checked||this._busy||Object.keys(this._preview?.errors||{}).length>0;});
    this.shadowRoot.querySelector('#apply')?.addEventListener('click',()=>this.apply());
    this.shadowRoot.querySelector('#cancel')?.addEventListener('click',async()=>{await this.invalidate();this.render();});
    this.shadowRoot.querySelector('#device')?.addEventListener('change',async event=>{await this.invalidate();this._entryId=event.target.value;this._busy=true;this._error='';this._success='';this.render();try{await this.status(true);}catch{this._error='读取设备失败。';}finally{this._busy=false;this.render();}});
  }
}
if(!customElements.get('cocan-broker-settings'))customElements.define('cocan-broker-settings',CocanBrokerSettings);

class CocanSettingsDialog extends HTMLElement {
  constructor(){super();this.attachShadow({mode:'open'});this._onKey=event=>{
      if(event.key==='Escape'&&!this._editor?._busy){event.preventDefault();this.closeDialog();}
      if(event.key==='Tab'){
        const nodes=[this.shadowRoot.querySelector('#close'),...this._editor?.shadowRoot.querySelectorAll('button:not([disabled]),input:not([disabled]),select:not([disabled]),a[href]')||[]].filter(Boolean);
        const active=event.composedPath()[0],index=nodes.indexOf(active);
        if(event.shiftKey&&index<=0){event.preventDefault();nodes.at(-1)?.focus();}
        else if(!event.shiftKey&&(index===nodes.length-1||index<0)){event.preventDefault();nodes[0]?.focus();}
      }
    };}
  set hass(value){this._hass=value;if(this._editor)this._editor.hass=value;}
  async showDialog(params){
    this._params=params;this._previousFocus=document.activeElement;
    this.shadowRoot.innerHTML=`<style>:host{position:fixed;inset:0;z-index:1000;display:grid;place-items:center;background:#0007}.dialog{width:min(1040px,calc(100vw - 48px));height:min(900px,calc(100dvh - 48px));border-radius:20px;background:var(--primary-background-color);color:var(--primary-text-color);box-shadow:0 16px 64px #0006;display:flex;flex-direction:column;overflow:hidden}header{display:flex;align-items:center;justify-content:space-between;padding:16px 24px;border-bottom:1px solid var(--divider-color)}h2{font-size:21px;margin:0}button{border:0;background:transparent;color:inherit;font:inherit;font-size:26px;cursor:pointer;padding:4px 10px}cocan-broker-settings{flex:1;min-height:0}@media(max-width:600px){.dialog{width:100vw;height:100dvh;border-radius:0}}</style><section class="dialog" role="dialog" aria-modal="true" aria-labelledby="settings-title"><header><h2 id="settings-title">小电拼配置</h2><button id="close" aria-label="关闭">×</button></header></section>`;
    const editor=document.createElement('cocan-broker-settings');editor.entryId=params.entry_id;editor.embedded=true;editor.advancedAvailable=Boolean(params.originalDialog);this._editor=editor;
    this.shadowRoot.querySelector('section').append(editor);editor.hass=this._hass;
    this.shadowRoot.querySelector('#close').onclick=()=>this.closeDialog();
    editor.addEventListener('cocan-advanced-settings',()=>{
      const original=this._params.originalDialog;if(!original)return;
      const source=this._params.sourceElement||document.querySelector('home-assistant');
      this.closeDialog();
      const flow=original.dialogParams.flowConfig;
      const advancedFlow={...flow,createFlow:async(hass,handler)=>{
        const start=await flow.createFlow(hass,handler);
        return start.type==='menu'?flow.handleFlowStep(hass,start.flow_id,{next_step_id:'settings'}):start;
      }};
      source?.dispatchEvent(new CustomEvent('show-dialog',{bubbles:true,composed:true,detail:{...original,dialogParams:{...original.dialogParams,flowConfig:advancedFlow,_cocanNative:true}}}));
    });
    this.addEventListener('keydown',this._onKey);this.shadowRoot.querySelector('#close').focus();
  }
  closeDialog(){
    if(this._editor?._busy)return false;
    this._editor?.remove();this._editor=null;this.removeEventListener('keydown',this._onKey);
    this.shadowRoot.replaceChildren();
    this.dispatchEvent(new CustomEvent('dialog-closed',{bubbles:true,composed:true,detail:{dialog:this.localName}}));
    this._params?.dialogClosedCallback?.({flowFinished:false});this._previousFocus?.focus?.();return true;
  }
}
if(!customElements.get('cocan-settings-dialog'))customElements.define('cocan-settings-dialog',CocanSettingsDialog);

// HA's integration gear emits this dialog event. Change only this integration's
// options editor; creation flows, resumed flows and all other integrations pass
// through untouched. No DOM observers or changes to HA element prototypes.
if(!window.__cocanSettingsDialogHook){
  window.__cocanSettingsDialogHook=true;
  window.addEventListener('show-dialog',event=>{
    const detail=event.detail,params=detail?.dialogParams;
    if(detail?.dialogTag!=='dialog-data-entry-flow'||params?.domain!=='mcp_cocan'||params?.flowConfig?.flowType!=='options_flow'||!params.startFlowHandler||params.continueFlowId||params._cocanNative)return;
    const original={...detail,dialogParams:{...params}};
    detail.dialogTag='cocan-settings-dialog';detail.dialogImport=()=>Promise.resolve();
    detail.dialogParams={entry_id:params.startFlowHandler,originalDialog:original,sourceElement:params.dialogParentElement,dialogClosedCallback:params.dialogClosedCallback};
  },{capture:true});
}
