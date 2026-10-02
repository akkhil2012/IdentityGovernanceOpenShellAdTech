import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Pipeline} from './Pipeline';
import './style.css';

const API=import.meta.env.VITE_API_URL || 'http://localhost:8000';
type AnyData=Record<string,any>;
type Tab='control-room'|'propensity'|'openshell';
const initial={name:'Loyalty upgrade',request:'Find customers likely to upgrade',purpose:'personalized_advertising',channel:'display',destination:'mock-dsp',max_audience:100};

const scoreProfile=(profile:any)=>1/(1+Math.exp(-(-2.2+.055*profile.visits_30d+.24*profile.purchases_180d-.003*profile.days_since_purchase+.0012*profile.avg_order_value)));

function PropensityScoring({profiles}:{profiles:any[]}){
 const ranked=profiles.map(profile=>({...profile,score:scoreProfile(profile)})).sort((a,b)=>b.score-a.score);
 return <section className="tab-panel" id="propensity-panel" role="tabpanel" aria-labelledby="propensity-tab">
  <div className="section-intro"><div><span className="eyebrow">TRANSPARENT · ILLUSTRATIVE · NON-SENSITIVE</span><h2>Propensity scoring</h2><p>See how eligible profiles are ranked before consent and policy decide who can enter an audience.</p></div><div className="score-badge"><small>MODEL TYPE</small><strong>Logistic baseline</strong><span>No learned weights</span></div></div>
  <div className="walkthrough"><article><span>01</span><h3>Eligibility first</h3><p>Ineligible profiles are removed before scoring. A high score can never restore eligibility.</p></article><article><span>02</span><h3>Score allowed features</h3><p>Only visits, purchases, recency, and average order value contribute. No sensitive attributes are used.</p></article><article><span>03</span><h3>Rank, then check consent</h3><p>Scores order candidates; current consent and governance still determine approval. A score is not permission.</p></article></div>
  <div className="formula-card"><div><small>FIXED SCORING FUNCTION</small><code>σ(−2.2 + 0.055·visits + 0.24·purchases − 0.003·days + 0.0012·AOV)</code></div><p><b>Important:</b> This synthetic score estimates demo propensity only. It does not prove causality, incremental lift, identity, or consent.</p></div>
  <section className="card score-table"><div className="title"><span>LIVE SAMPLE</span><h3>How the visible profiles rank</h3><i className="legend">HIGHEST FIRST</i></div><div className="table-scroll"><table><thead><tr><th>Rank</th><th>Customer</th><th>Visits</th><th>Purchases</th><th>Recency</th><th>AOV</th><th>Score</th><th>Eligibility gate</th></tr></thead><tbody>{ranked.map((p,index)=><tr key={p.customer_id} className={!p.eligible?'row-ineligible':''}><td>{index+1}</td><td>{p.customer_id}</td><td>{p.visits_30d}</td><td>{p.purchases_180d}</td><td>{p.days_since_purchase}d</td><td>${p.avg_order_value}</td><td><b className="score-value">{(p.score*100).toFixed(1)}%</b></td><td>{p.eligible?'Pass':'Excluded before scoring'}</td></tr>)}</tbody></table></div></section>
 </section>
}

function OpenShellGuide({config}:{config:AnyData}){
 const enabled=Boolean(config.isolated);
 const steps=enabled?[
  ['Coordinator validates authority','The API mints a signed, task-bound grant with one capability and a limited record budget.'],
  ['Broker dispatches remotely','The typed task envelope is authenticated and sent to the configured worker URL.'],
  ['OpenShell isolates the worker','A separately deployed sandbox applies its operator-validated filesystem, process, and network policy.'],
  ['Result returns with evidence','The UI displays the real sandbox ID returned for each worker execution.'],
 ]:[
  ['Coordinator validates authority','The same signed grants, scopes, budgets, replay checks, and audit events are enforced.'],
  ['Worker runs in this process','The deterministic adapter executes locally; no request is sent to an isolated worker.'],
  ['Sandbox labels are illustrative','Configured simulation IDs show intended placement, not proof of an applied isolation policy.'],
  ['Result remains safe to demo','The destination is still a local mock, but host-level containment must not be claimed.'],
 ];
 return <section className="tab-panel" id="openshell-panel" role="tabpanel" aria-labelledby="openshell-tab">
  <div className="section-intro"><div><span className="eyebrow">RUNTIME BOUNDARY</span><h2>OpenShell mode</h2><p>A side-by-side explanation of what changes when workload isolation is enabled—and what governance remains in simulation.</p></div><div className={'runtime-state '+(enabled?'enabled':'disabled')}><span className="state-dot"/><div><small>CURRENT RUNTIME</small><strong>{enabled?'ENABLED · ISOLATED':'DISABLED · SIMULATION'}</strong><p>{enabled?'Remote workers must report configured sandbox IDs.':'Workers execute in the API process.'}</p></div></div></div>
  <div className="mode-compare"><article className={enabled?'selected':''}><div className="compare-title"><span>OPEN­SHELL ON</span>{enabled&&<b>CURRENT</b>}</div><h3>Separated execution boundary</h3><ul><li>Six remote, authenticated worker endpoints</li><li>Distinct sandbox and workload identity per agent</li><li>Operator-validated filesystem, process, and network restrictions</li><li>Startup fails closed when required configuration is missing</li></ul></article><article className={!enabled?'selected':''}><div className="compare-title"><span>OPEN­SHELL OFF</span>{!enabled&&<b>CURRENT</b>}</div><h3>Deterministic simulation</h3><ul><li>Workers execute in process with a fixed seed</li><li>Governance grants and policy denials still execute</li><li>No process or network isolation is provided</li><li>Sandbox names are labels—not isolation evidence</li></ul></article></div>
  <section className="card journey"><div className="title"><span>RUNTIME WALKTHROUGH</span><h3>What happens in the current mode</h3></div><ol>{steps.map(([title,detail],index)=><li key={title}><span>{String(index+1).padStart(2,'0')}</span><div><h4>{title}</h4><p>{detail}</p></div></li>)}</ol></section>
  <div className="boundary-note"><b>Unchanged in both modes</b><p>Eligibility precedes scoring; consent is checked before approval and again at activation; grants are narrow and short-lived; payloads are digest-bound; activation is idempotent; and the destination remains a non-sending mock.</p></div>
 </section>
}

function App(){
 const [config,setConfig]=useState<AnyData>({mode:'loading',scenarios:{},sandboxes:{}}),[brief,setBrief]=useState(initial),[scenario,setScenario]=useState('authorized_success');
 const [result,setResult]=useState<AnyData|null>(null),[profiles,setProfiles]=useState<any[]>([]),[busy,setBusy]=useState(false),[receipt,setReceipt]=useState<AnyData|null>(null),[tab,setTab]=useState<Tab>('control-room');
 useEffect(()=>{fetch(API+'/api/config').then(r=>r.json()).then(setConfig);fetch(API+'/api/profiles?limit=12').then(r=>r.json()).then(x=>setProfiles(x.items))},[]);
 async function run(){setBusy(true);setReceipt(null);const r=await fetch(API+'/api/workflows',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({brief,scenario})});setResult(await r.json());setBusy(false)}
 async function activate(){if(!result)return;const r=await fetch(API+'/api/activate',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({workflow_id:result.workflow_id,idempotency_key:'demo-'+result.workflow_id})});setReceipt(await r.json())}
 async function withdraw(){alert('Select the “Consent withdrawal after approval” scenario to deterministically revoke an approved member before activation.')}
 const tabs:[Tab,string][]=[['control-room','Control room'],['propensity','Propensity scoring'],['openshell','OpenShell']];
 return <main><header><div><span className="eyebrow">IDENTITY GOVERNANCE · ADTECH</span><h1>Audience Control Room</h1></div><span className={'mode '+(config.isolated?'real':'sim')}>{config.isolated?'OPEN­SHELL ISOLATED':'⚠ SIMULATION — NOT ISOLATED'}</span></header>
 <nav className="tabs" role="tablist" aria-label="Audience governance views">{tabs.map(([id,label])=><button key={id} id={`${id}-tab`} role="tab" aria-selected={tab===id} aria-controls={`${id}-panel`} className={tab===id?'active':''} onClick={()=>setTab(id)}>{label}{id==='openshell'&&<i className={config.isolated?'on':'off'}>{config.isolated?'ON':'OFF'}</i>}</button>)}</nav>
 {tab==='propensity'?<PropensityScoring profiles={profiles}/>:tab==='openshell'?<OpenShellGuide config={config}/>:<section id="control-room-panel" role="tabpanel" aria-labelledby="control-room-tab">
 <section className="hero"><div><h2>From intent to activation,<br/><em>with authority attached.</em></h2><p>Consent-aware ranking. Narrow delegation. Immutable activation permits.</p></div><div className="decision"><small>ACTIVATION DECISION</small><strong className={(result?.decision||'WAIT').toLowerCase()}>{result?.decision||'WAITING'}</strong><span>{result?.reason||'Run a governed workflow'}</span></div></section>
 <div className="grid"><section className="card brief"><div className="title"><span>01</span><h3>Campaign brief</h3></div><label>Campaign<input value={brief.name} onChange={e=>setBrief({...brief,name:e.target.value})}/></label><label>Manager request<textarea value={brief.request} onChange={e=>setBrief({...brief,request:e.target.value})}/></label><div className="row"><label>Scenario<select value={scenario} onChange={e=>setScenario(e.target.value)}>{Object.entries(config.scenarios||{}).map(([k,v])=><option value={k} key={k}>{String(v)}</option>)}</select></label><label>Max audience<input type="number" value={brief.max_audience} onChange={e=>setBrief({...brief,max_audience:+e.target.value})}/></label></div><button onClick={run} disabled={busy}>{busy?'Coordinating…':'Run governed workflow →'}</button></section>
 <section className="card"><div className="title"><span>02</span><h3>Audience funnel</h3></div>{result?.funnel?<><div className="metrics"><b>{result.funnel.generated}<small>generated</small></b><b>{result.funnel.eligible}<small>eligible</small></b><b>{result.funnel.approved}<small>approved</small></b></div><div className="bar"><i style={{width:(result.funnel.approved/result.funnel.generated*100)+'%'}}/></div><p className="muted">Exclusions: {JSON.stringify(result.funnel.excluded)}</p></>:<p className="empty">Funnel appears after a run.</p>}<div className="actions"><button className="secondary" onClick={withdraw}>Withdraw consent</button><button onClick={activate} disabled={result?.decision!=='GO'}>Activate mock</button></div>{receipt&&<pre>{JSON.stringify(receipt,null,2)}</pre>}</section>
 <section className="card wide"><div className="title"><span>03</span><h3>Agent execution pipeline</h3><i className="legend">GOVERNANCE / SANDBOX</i></div><Pipeline stages={result?.timeline||Object.keys(config.sandboxes||{}).map(agent=>({agent,status:'idle',sandbox_id:config.sandboxes[agent],governance:'pending'}))}/></section>
 <section className="card wide"><div className="title"><span>04</span><h3>Delegation inspector</h3></div>{result?.grants?.length?<div className="grants">{result.grants.map((g:any)=><article key={g.grant_id}><b>{g.subject}</b><code>{g.grant_id}</code><p>{g.capabilities.join(', ')} · {g.record_budget} records</p><small>{g.root_subject} → {g.parent_grant||'root'} · expires {new Date(g.expires_at).toLocaleTimeString()}</small></article>)}</div>:<p className="empty">Signed, narrowed task grants appear here. Agents cannot mint authority.</p>}</section>
 {result?.identity_evidence&&<section className="card wide"><div className="title"><span>ID</span><h3>Runtime identity evidence</h3><i className="legend">ON BEHALF OF ≠ RUN AS</i></div><div className="formula-card"><div><small>PRINCIPAL</small><code>{result.identity_evidence.principal||'agent principals minted per task'}</code></div><p><b>Fabio supplied the intent.</b> {result.identity_evidence.explanation}</p></div><pre>{JSON.stringify(result.identity_evidence,null,2)}</pre></section>}
 <section className="card wide"><div className="title"><span>05</span><h3>Synthetic profile explorer</h3><i className="legend">ILLUSTRATIVE DATA</i></div><table><thead><tr><th>Customer</th><th>Visits</th><th>Purchases</th><th>Recency</th><th>AOV</th><th>Eligible</th></tr></thead><tbody>{profiles.map(p=><tr key={p.customer_id}><td>{p.customer_id}</td><td>{p.visits_30d}</td><td>{p.purchases_180d}</td><td>{p.days_since_purchase}d</td><td>${p.avg_order_value}</td><td>{p.eligible?'Yes':'No'}</td></tr>)}</tbody></table></section></div></section>}
 <footer>No ads or emails are sent · Synthetic scores do not prove incremental lift · Policy v2026-01</footer></main>
}
createRoot(document.getElementById('root')!).render(<App/>);
