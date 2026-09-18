/* Suite do motor de cronograma.
   Roda as funcoes de calculo sobre o data.js real, sem navegador.
   Antes: python scripts/extrai_script.py    Depois: node scripts/teste_motor.js */
const fs=require('fs'),path=require('path');
const raiz=path.join(__dirname,'..');
const app=fs.readFileSync(path.join(raiz,'.tmp','app.js'),'utf8');
const helpers=app.match(/function diffDias[^\n]*\n/)[0]+app.match(/function addDias[^\n]*\n/)[0];
const motor=app.slice(app.indexOf('/* -------- cronograma: linha de base'),app.indexOf('function statusProcesso(p,hoje){'));
const esc=t=>t==null?'':String(t);
const win={};
eval(fs.readFileSync(path.join(raiz,'data.js'),'utf8').replace('window.','win.'));
let db=JSON.parse(JSON.stringify(win.LIEBE_SEED));
const window={LIEBE_SEED:win.LIEBE_SEED};
// stubs do ambiente de navegador que o motor usa para saber a colecao ativa
const LS_COL='liebe_colecao';
const localStorage={_v:{},getItem(k){return this._v[k]||null},setItem(k,v){this._v[k]=v}};
const ST={cronograma:{}};
eval(helpers+motor);

const HOJE='2026-09-17';
let falhas=0;
const ok=(c,m)=>{console.log((c?'  OK   ':'  FALHA')+' '+m); if(!c)falhas++};

console.log('\n=== 1. Trilha paralela nunca e empurrada ===');
const base=projetarCronograma(HOJE), sim1=projetarCronograma(HOJE,{1:30});
[5,14,34].forEach(s=>ok(base[s].fim===sim1[s].fim,'#'+s+' imovel com atraso de 30d na #1 ('+base[s].fim+')'));

console.log('\n=== 2. Etapa sem sucessor nao empurra ninguem ===');
[23,37,33].forEach(s=>{const r=simularAtraso(s,15,HOJE);ok(r.afetados.length===0,'#'+s+' atrasando 15d nao afeta ninguem')});

console.log('\n=== 3. Confere com o calculo da planilha ===');
const d25=diffDias(db.macro_processes.find(p=>p.seq===25).end_date,base[25].fim);
const d21=diffDias(db.macro_processes.find(p=>p.seq===21).end_date,base[21].fim);
ok(d25===61,'#25 Liberacao para o PCP = +61 dias (calculado '+d25+')');
ok(d21===82,'#21 Analise de precos e custos = +82 dias (calculado '+d21+')');

console.log('\n=== 4. Margem de manobra ===');
const mgPcp=margemCronograma(HOJE,{seq:25}), mgEnt=margemCronograma(HOJE,{data:dataEntrega()});
ok(mgPcp[14].dentro===false,'#14 (isolada) fora da cadeia do PCP');
const sit14=situacaoProc(db.macro_processes.find(p=>p.seq===14),base,mgPcp);
ok(sit14.critico===false&&sit14.paralelo===true,'#14 marcada como paralela e nunca critica');
console.log('  info  marco entrega='+dataEntrega()+' | margem #25 ate PCP='+mgPcp[25].dias+'d | ate entrega='+mgEnt[25].dias+'d');

console.log('\n=== 5. Dado faltante nao vira numero inventado ===');
[17,28,38,39].forEach(s=>ok(base[s].origem==='indefinido'&&base[s].fim===null,'#'+s+' sem datas -> "indefinido"'));
db.macro_processes.push({seq:99,id:'proc-99',name:'sintetico',macro_tema:'Mostruário',predecessores:[17],collection_id:db.macro_processes[0].collection_id,
  start_date:'2026-10-01',end_date:'2026-10-10',inicio_real:null,fim_real:null,completed_at:null,percent_complete:0});
ok(projetarCronograma(HOJE)[99].incompleto===true,'etapa em aberto que depende da #17 -> projecao incompleta');
db.macro_processes.pop();

console.log('\n=== 6. Etapa ja concluida nao comporta simulacao ===');
const r24=simularAtraso(24,10,HOJE);
ok(r24.jaConcluida===true&&r24.empurra===false,'#24 ja concluida -> marcada como tal, sem impacto falso');

console.log('\n=== 7. Simulacao nas etapas ainda EM ABERTO ===');
const abertas=db.macro_processes.filter(p=>!(p.fim_real||p.completed_at)).map(p=>p.seq);
console.log('  em aberto hoje: '+abertas.join(', '));
let algumEmpurra=false;
abertas.forEach(s=>{const r=simularAtraso(s,10,HOJE);
  if(r.empurra){algumEmpurra=true;console.log('    #'+s+' +10d -> empurra '+r.afetados.map(a=>'#'+a.seq+'(+'+a.dias+'d)').join(' ')+' | PCP '+r.pcp+'d')}
  else console.log('    #'+s+' +10d -> nao empurra ninguem'+(r.jaConcluida?' (concluida)':''))});
ok(algumEmpurra,'ao menos uma etapa em aberto propaga atraso (a cadeia esta viva)');

console.log(falhas?'\n'+falhas+' FALHA(S)':'\nTODOS OS TESTES PASSARAM');
process.exit(falhas?1:0);
