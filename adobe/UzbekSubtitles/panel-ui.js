/* global __adobe_cep__ */
(function(){
  'use strict';
  function el(id){return document.getElementById(id);}
  var host='';try{host=JSON.parse(__adobe_cep__.getHostEnvironment()).appName;}catch(_){}
  document.body.setAttribute('data-host',host);
  el('hostBadge').textContent=host==='AEFT'?'After Effects':host==='PPRO'?'Premiere Pro':'';
  if(host==='AEFT')el('captionGuide').textContent='Bitta video layerni tanlang. Subtitrni yarating va timeline’ga qo‘shing.';
  var ids=['captionsTab','textToolsTab','podcastTab','reelsTab'],nav=document.querySelector('.mode-tabs'),account=el('support');
  function syncTabs(){ids.forEach(function(id){var tab=el(id);tab.tabIndex=tab.getAttribute('aria-selected')==='true'&&!tab.hidden?0:-1;});}
  function modelLabel(){var model=el('model'),option=model.options[model.selectedIndex];el('modelSummary').textContent=option?option.textContent:'Avtomatik';}
  el('model').addEventListener('change',modelLabel);modelLabel();syncTabs();
  ids.forEach(function(id){el(id).addEventListener('click',function(){syncTabs();account.open=false;});});
  nav.addEventListener('keydown',function(event){if(['ArrowLeft','ArrowRight','Home','End'].indexOf(event.key)<0 || ids.indexOf(event.target.id)<0 || document.uzscribeBusy)return;
    var tabs=ids.map(el).filter(function(tab){return !tab.hidden&&!tab.disabled;}),index=tabs.indexOf(event.target);if(index<0||!tabs.length)return;
    event.preventDefault();var next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;tabs[next].click();tabs[next].focus();syncTabs();
  });
  document.addEventListener('mousedown',function(){document.body.setAttribute('data-input','pointer');});
  document.addEventListener('keydown',function(event){document.body.setAttribute('data-input','keyboard');if(event.key==='Escape'&&account.open){account.open=false;account.querySelector('summary').focus();}});
  document.addEventListener('click',function(event){if(account.open&&!account.contains(event.target))account.open=false;});
  // Visibility/selection also changes in the native workflow adapters.
  if(typeof MutationObserver!=='undefined')new MutationObserver(syncTabs).observe(nav,{attributes:true,subtree:true,attributeFilter:['hidden','aria-selected']});
}());
