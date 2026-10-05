/* global __adobe_cep__ */
(function(){
  'use strict';
  var bridge=document.uzscribe,busy=false;
  function el(id){return document.getElementById(id);}
  function isAE(){try{return JSON.parse(__adobe_cep__.getHostEnvironment()).appName==='AEFT';}catch(_){return false;}}
  var tabs=['captionsTab','podcastTab','reelsTab','textToolsTab'];
  function available(){return isAE() && !busy && !document.uzscribeBusy;}
  function call(expr,done){bridge.aeHost(expr,function(error,raw){if(error)return done(error);try{var data=JSON.parse(raw);done(data.error?new Error(data.error):null,data);}catch(e){done(new Error('After Effects javobi o‘qilmadi.'));}});}
  function refresh(){if(!available())return;call('uzTextSplitInfo()',function(error,data){el('textToolsInfo').textContent=error?error.message:data.name+' · '+data.words+' ta so‘z';});}
  el('textToolsTab').hidden=!isAE();
  el('textToolsTab').addEventListener('click',function(){if(!available())return;['captionPage','podcastPage','reelsPage'].forEach(function(id){el(id).hidden=true;});el('textToolsPage').hidden=false;tabs.forEach(function(id){el(id).setAttribute('aria-selected',String(id==='textToolsTab'));});refresh();});
  ['captionsTab','podcastTab','reelsTab'].forEach(function(id){el(id).addEventListener('click',function(){if(busy||document.uzscribeBusy)return;el('textToolsPage').hidden=true;el('textToolsTab').setAttribute('aria-selected','false');});});
  el('textToolsRefresh').onclick=refresh;
  el('textToolsSplit').onclick=function(){if(!available())return;busy=true;document.uzscribeBusy=true;tabs.concat(['textToolsRefresh','textToolsSplit']).forEach(function(id){el(id).disabled=true;});el('textToolsStatus').textContent='So‘z layerlari yaratilmoqda…';call('uzSplitTextWords()',function(error,data){busy=false;document.uzscribeBusy=false;tabs.concat(['textToolsRefresh','textToolsSplit']).forEach(function(id){el(id).disabled=false;});el('textToolsStatus').textContent=error?error.message:data.count+' ta so‘z layeri yaratildi. Asl layer saqlandi.';});};
}());
