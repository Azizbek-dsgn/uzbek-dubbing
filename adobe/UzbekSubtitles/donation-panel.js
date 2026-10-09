(function () {
  'use strict';
  var URL='https://taps.uz/fikrosfera/d', KEY='uzscribe.donation.v2';
  var notice=document.getElementById('donationNotice'),support=document.getElementById('support');
  var link=document.getElementById('donateLink'),status=document.getElementById('donationStatus');
  if(!notice||!support||!link||!status)return;
  notice.hidden=false;
  // Count panel loads, not tab changes, clicks or returns from the browser.
  try {
    var state=JSON.parse(localStorage.getItem(KEY)||'{}');
    var count=typeof state.opens==='number'&&isFinite(state.opens)&&state.opens>=0&&state.opens<5&&Math.floor(state.opens)===state.opens?state.opens:0;
    count=(count+1)%5;
    localStorage.setItem(KEY,JSON.stringify({opens:count}));
    if(count===0)support.open=true;
  } catch (_) { /* The pinned notice and manual QR still work without storage. */ }
  document.getElementById('donationShow').onclick=function(event){
    if(event)event.stopPropagation();support.open=true;link.focus();
  };
  function failed(){status.textContent='Brauzer ochilmadi. QR kodni skanerlang yoki taps.uz/fikrosfera/d havolasini brauzerda oching.';}
  link.onclick=function(event){
    status.textContent='';
    var util=typeof window!=='undefined'&&window.cep&&window.cep.util;
    var inAdobe=!!util||typeof __adobe_cep__!=='undefined';
    if(!inAdobe&&typeof require!=='function')return; // Regular browser: use the anchor.
    if(event)event.preventDefault();
    if(util&&typeof util.openURLInDefaultBrowser==='function'){
      try {var result=util.openURLInDefaultBrowser(URL);if(result===0||typeof result==='undefined')return;}catch(_){}
    }
    // CEP's browser bridge may be missing or return an error. Use the OS launcher.
    try {
      var cp=require('child_process');
      if(process.platform==='darwin')cp.execFile('/usr/bin/open',[URL],function(error){if(error)failed();});
      else if(process.platform==='win32'){
        var path=require('path'),system=process.env.SystemRoot||'C:\\Windows';
        cp.execFile(path.join(system,'System32','rundll32.exe'),['url.dll,FileProtocolHandler',URL],{windowsHide:true},function(error){if(error)failed();});
      }else failed();
    }catch(_){failed();}
  };
}());
