/* Adaptador de leitura no navegador. Sem API remota, persistência de base ou escrita. */
(()=>{
'use strict';
let loaded=null;let pending=null;
const copy=v=>JSON.parse(JSON.stringify(v));
const apiRoot='/api/panel/';
async function bundle(){
 if(loaded)return loaded;
 if(!pending)pending=(async()=>{
  const response=await fetch(new URL('../data/demo.json',document.currentScript?.src||new URL('./assets/adapter.js',location.href)),{cache:'no-cache'});
  if(!response.ok)throw Error('Artefato sintético não encontrado. Confira o deploy e recarregue.');
  const data=await response.json();
  if(data.synthetic!==true||data.schema_version!=='1.0'||!data.scenarios?.normal)throw Error('Contrato do artefato público incompatível.');
  loaded=data;return data;
 })().catch(e=>{pending=null;throw e});
 return pending;
}
function mask(value,reveal){
 const r=copy(value);if(reveal)return r;
 const hide=x=>{if(x.name)x.name=x.name.slice(0,1)+'***';if(x.email)x.email=x.email.includes('@')?'***@example.test':'***';if(x.phone)x.phone='***'+x.phone.slice(-4)};
 hide(r);
 for(const source of ['crm','omnichannel'])for(const c of r[source]?.candidates||[]){hide(c);for(const key of c.keys){if(key.kind==='email')key.value='***@example.test';if(key.kind==='phone')key.value='***'+key.value.slice(-4)}}
 return r;
}
function paginate(rows,q){
 const integer=(name,def,max)=>{const v=q.get(name)||String(def);if(!/^\d+$/.test(v)||+v<1||+v>max)throw Error('Página/tamanho inválido.');return +v};
 const size=integer('size',25,100),pages=Math.max(1,Math.ceil(rows.length/size)),page=Math.min(integer('page',1,1000000),pages);
 return {rows:rows.slice((page-1)*size,page*size),total:rows.length,page,pages,size};
}
const state={scenario:'normal',stage:0,traceId:'DEMO-CORE-00008',
 reset(){this.scenario='normal';this.stage=0;this.traceId='DEMO-CORE-00008'},
 get bundle(){return loaded},
 get current(){return loaded?.scenarios[this.scenario]},
 controls(){return '<section class="site-controls" aria-label="Controles da sessão de demonstração"><label><span>Cenário sintético</span><select id="scenario-select" aria-label="Cenário sintético">'+[['normal','Todas as fontes disponíveis'],['crm-off','CRM indisponível'],['core-off','ERP Core indisponível'],['omni-off','Omnichannel indisponível']].map(([key,text])=>'<option value="'+key+'" '+(this.scenario===key?'selected':'')+'>'+text+'</option>').join('')+'</select></label><p>Interações apenas nesta sessão.<br>Recarregar restaura a base inicial.</p><button type="button" class="live-button" data-action="restore-demo">Restaurar demonstração</button></section>'},
 async api(path){
  const data=await bundle(),scenario=data.scenarios[this.scenario];
  if(!scenario)throw Error('Cenário sintético inválido.');
  const url=new URL(path,location.origin);if(!url.pathname.startsWith(apiRoot))throw Error('Rota não permitida.');
  const q=url.searchParams;for(const key of q.keys())if(!['source','search','page','size','issue','status','reveal','id'].includes(key)||q.getAll(key).length!==1)throw Error('Parâmetro inválido.');
  if(!['0','1'].includes(q.get('reveal')||'0'))throw Error('Opção de exibição inválida.');
  const reveal=q.get('reveal')==='1',search=(q.get('search')||'').toLocaleLowerCase('pt-BR');if(search.length>200)throw Error('Busca maior que 200 caracteres.');
  const matches=r=>!search||JSON.stringify(r).toLocaleLowerCase('pt-BR').includes(search);
  const route=url.pathname.slice(apiRoot.length);
  if(route==='overview')return copy(scenario.overview);
  if(route==='records'){
   const source=q.get('source')||'core',issue=q.get('issue')||'all';
   if(!['core','crm','omnichannel'].includes(source))throw Error('Fonte inválida.');
   if(!Object.hasOwn(scenario.overview.issues,issue))throw Error('Fila inválida.');
   if(scenario.records[source]===null)throw Error('Fonte sintética indisponível; não significa zero registros.');
   return paginate(scenario.records[source].filter(r=>(issue==='all'||r.issues.includes(issue))&&matches(r)).map(r=>mask(r,reveal)),q);
  }
  if(route==='reconciliation'){
   if(scenario.reconciliation===null)return {available:false,rows:[],total:null,message:'ERP Core indisponível: universo de comparação não definido.'};
   const status=q.get('status')||'all';if(status!=='all'&&!Object.hasOwn(scenario.overview.statuses,status))throw Error('Situação inválida.');
   return {available:true,...paginate(scenario.reconciliation.filter(r=>(status==='all'||['crm','omnichannel'].some(s=>r[s].status===status))&&matches(r)).map(r=>mask(r,reveal)),q)};
  }
  if(route==='evidence'){const row=scenario.reconciliation?.find(r=>r.id===q.get('id'));if(!row)throw Error('Cadastro Core não encontrado.');return mask(row,reveal)}
  if(route==='conversations'){if(scenario.records.conversations===null)throw Error('Omnichannel indisponível; conversas não avaliadas.');return paginate(scenario.records.conversations.filter(matches).map(copy),q)}
  if(route==='messages'){if(scenario.records.conversations===null)throw Error('Omnichannel indisponível.');if(!scenario.records.conversations.some(r=>r.id===q.get('id')))throw Error('Conversa não encontrada.');return {rows:scenario.records.messages.filter(r=>r.conversation_id===q.get('id')).map(copy)}}
  throw Error('Rota do painel não encontrada.');
 }
};window.PrismaStatic=state;
})();
