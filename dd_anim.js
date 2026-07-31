// DecideDeck scene generator (JSON-driven). Reads a rounds config and writes
// one animated HTML per round; each exposes window.setT(t) for the frame grabber.
// Usage: node dd_anim.js <rounds.json> <outdir>
//   rounds.json = [{pal, head, sub, la, lb, imgA, imgB, sa, sb, pa, pb, win, vl}]
const fs = require('fs');
const path = require('path');
const [,, roundsPath, outdir] = process.argv;
const rounds = JSON.parse(fs.readFileSync(roundsPath, 'utf8'));

const b64 = (p) => 'data:image/jpeg;base64,' + fs.readFileSync(p).toString('base64');
const esc = (s) => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

const WARM = {
  sunset:{felt:'radial-gradient(80% 62% at 50% 44%,#FF8A5B 0%,#FF4E6B 52%,#C81E4B 100%)',gold:'#FFD23F',plaque:'#8E1636',headStroke:'#5c0e24',
    a:{accent:'#FB7185',edge:'#9F1239',chipTxt:'#fff',glow:'rgba(251,113,133,.72)'}, b:{accent:'#F97316',edge:'#9A3412',chipTxt:'#fff',glow:'rgba(249,115,22,.72)'}},
  gold:{felt:'radial-gradient(80% 62% at 50% 44%,#FBBF24 0%,#D97706 52%,#7C2D12 100%)',gold:'#FDE047',plaque:'#7C2D12',headStroke:'#4a1a08',
    a:{accent:'#F59E0B',edge:'#B45309',chipTxt:'#3a2600',glow:'rgba(245,158,11,.72)'}, b:{accent:'#EA580C',edge:'#9A3412',chipTxt:'#fff',glow:'rgba(234,88,12,.72)'}},
  forest:{felt:'radial-gradient(80% 62% at 50% 44%,#4ADE80 0%,#16A34A 52%,#14532D 100%)',gold:'#FDE047',plaque:'#166534',headStroke:'#0b3d1f',
    a:{accent:'#22C55E',edge:'#15803D',chipTxt:'#fff',glow:'rgba(34,197,94,.72)'}, b:{accent:'#EAB308',edge:'#854D0E',chipTxt:'#3a2600',glow:'rgba(234,179,8,.72)'}},
  ocean:{felt:'radial-gradient(80% 62% at 50% 44%,#38BDF8 0%,#2563EB 52%,#1E3A8A 100%)',gold:'#FFD23F',plaque:'#1E40AF',headStroke:'#0f2557',
    a:{accent:'#0EA5E9',edge:'#075985',chipTxt:'#fff',glow:'rgba(14,165,233,.72)'}, b:{accent:'#F97316',edge:'#9A3412',chipTxt:'#fff',glow:'rgba(249,115,22,.72)'}},
  grape:{felt:'radial-gradient(80% 62% at 50% 44%,#A78BFA 0%,#7C3AED 52%,#4C1D95 100%)',gold:'#FDE047',plaque:'#5B21B6',headStroke:'#3b1275',
    a:{accent:'#A855F7',edge:'#6B21A8',chipTxt:'#fff',glow:'rgba(168,85,247,.72)'}, b:{accent:'#EC4899',edge:'#9D174D',chipTxt:'#fff',glow:'rgba(236,72,153,.72)'}},
  midnight:{felt:'radial-gradient(80% 62% at 50% 44%,#3730A3 0%,#1E1B4B 52%,#0B1020 100%)',gold:'#FBBF24',plaque:'#312E81',headStroke:'#0b0a24',
    a:{accent:'#22D3EE',edge:'#0E7490',chipTxt:'#053345',glow:'rgba(34,211,238,.72)'}, b:{accent:'#F472B6',edge:'#9D174D',chipTxt:'#fff',glow:'rgba(244,114,182,.72)'}},
};

function suitBg(color){const s=['♠','♥','♦','♣'];let o='<div style="position:absolute;inset:0;overflow:hidden;opacity:.06">';let n=0;
  for(let r=0;r<11;r++)for(let c=0;c<6;c++){o+=`<div style="position:absolute;left:${c*190+(r%2?60:-20)}px;top:${r*180-40}px;font-family:'Baloo 2';font-size:120px;color:${color};transform:rotate(-15deg)">${s[n++%4]}</div>`;}return o+'</div>';}
const deck=(sz)=>`<svg width="${sz}" height="${sz}" viewBox="0 0 200 200" style="filter:drop-shadow(0 6px 10px rgba(0,0,0,.4))">
  <g transform="translate(100 104) rotate(-20)"><rect x="-52" y="-74" width="104" height="150" rx="18" fill="#1FD1A5"/></g>
  <g transform="translate(100 104) rotate(20)"><rect x="-52" y="-74" width="104" height="150" rx="18" fill="#FFC93C"/></g>
  <g transform="translate(100 100) rotate(-3)"><rect x="-54" y="-77" width="108" height="154" rx="20" fill="#fff"/>
  <path d="M -27 4 L -6 26 L 33 -27" fill="none" stroke="#7C3AED" stroke-width="17" stroke-linecap="round" stroke-linejoin="round"/></g></svg>`;
const chip=(id,fill,txt)=>`<svg id="${id}" width="180" height="180" viewBox="0 0 240 240" style="filter:drop-shadow(0 10px 16px rgba(0,0,0,.35))">
  <circle cx="120" cy="120" r="112" fill="${fill}"/><circle cx="120" cy="120" r="112" fill="none" stroke="#fff" stroke-width="18" stroke-dasharray="30 26"/>
  <circle cx="120" cy="120" r="84" fill="none" stroke="rgba(255,255,255,.55)" stroke-width="6"/>
  <text class="pct" x="120" y="150" text-anchor="middle" font-family="Baloo 2" font-weight="800" font-size="84" fill="${txt}">0%</text></svg>`;
const cardMarkup=(id,img,suit,label,side,fit)=>`
  <div class="pc" id="${id}" style="border-color:${side.edge}">
    <div class="crown" id="${id}crown">👑</div>
    <div class="ribbon" id="${id}rib" style="background:${side.accent};color:${side.chipTxt}">WINNER</div>
    <div class="pip tl" style="color:${side.edge}"><div>A</div><div>${suit}</div></div>
    <div class="pip br" style="color:${side.edge}"><div>A</div><div>${suit}</div></div>
    <img class="pcimg" src="${img}" style="object-fit:${fit||'cover'};${fit==='contain'?'background:#fff;padding:22px;':''}">
    <div class="pcbody"><div class="pclabel">${esc(label)}</div>
      <div class="pcbar"><div class="pcfill" id="${id}fill" style="width:0%;background:${side.accent}"></div></div>
      <div class="pcchip" id="${id}chipwrap">${chip(id+'chip',side.accent,side.chipTxt)}</div>
    </div>
  </div>`;

function build(Q){
  const P = WARM[Q.pal] || WARM.sunset;
  const IA=b64(Q.imgA), IB=b64(Q.imgB);
  const GLOWA=`0 0 0 10px ${P.a.accent},0 0 46px 6px ${P.a.glow},0 40px 66px rgba(0,0,0,.55)`;
  const GLOWB=`0 0 0 10px ${P.b.accent},0 0 46px 6px ${P.b.glow},0 40px 66px rgba(0,0,0,.55)`;
  return `<!doctype html><html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box}html,body{width:1080px;height:1920px;background:#000}
.stage{width:1080px;height:1920px;position:relative;overflow:hidden;background:${P.felt};font-family:'Baloo 2',sans-serif}
.vig{position:absolute;inset:0;background:radial-gradient(74% 62% at 50% 46%,transparent 44%,rgba(0,0,0,.5) 100%)}
.rail{position:absolute;inset:26px;border-radius:96px;border:5px solid ${P.gold};opacity:.85}
.rail2{position:absolute;inset:44px;border-radius:82px;border:3px dashed ${P.gold};opacity:.5}
.spot{position:absolute;top:360px;left:50%;transform:translateX(-50%);width:1120px;height:1320px;background:radial-gradient(closest-side,rgba(255,255,255,.24),transparent 72%);border-radius:50%}
.plaque{position:absolute;top:70px;left:50%;transform:translateX(-50%);background:${P.plaque};border:5px solid ${P.gold};border-radius:30px;padding:20px 66px 24px;box-shadow:0 14px 28px rgba(0,0,0,.4);text-align:center;z-index:6;width:840px}
.plaque .t{font-family:'Luckiest Guy';font-size:80px;line-height:1;color:#fff;-webkit-text-stroke:5px ${P.headStroke};paint-order:stroke fill}
.plaque .s{font-family:'Poppins';font-weight:700;font-size:30px;letter-spacing:8px;color:${P.gold};margin-top:10px}
.tbl{position:absolute;top:498px;left:0;width:100%;display:flex;justify-content:center;align-items:flex-end;gap:2px;z-index:3}
.pc{width:462px;height:1168px;background:#FFFDF8;border:11px solid #000;border-radius:44px;position:relative;display:flex;flex-direction:column;align-items:center;padding:22px 16px;transform-origin:50% 100%;box-shadow:0 26px 46px rgba(0,0,0,.45);will-change:transform}
.pc::after{content:'';position:absolute;inset:8px;border-radius:32px;border:3px solid rgba(36,28,59,.07);pointer-events:none}
.pip{position:absolute;font-family:'Baloo 2';font-weight:800;font-size:48px;text-align:center;line-height:.84;z-index:2}
.pip.tl{top:18px;left:26px}.pip.br{bottom:18px;right:26px;transform:rotate(180deg)}
.pcimg{width:414px;height:560px;border-radius:26px;object-fit:cover;z-index:2;box-shadow:0 12px 22px rgba(0,0,0,.25)}
.pcbody{flex:1;width:100%;display:flex;flex-direction:column;align-items:center;justify-content:space-between;padding:22px 8px 4px;z-index:2}
.pclabel{font-family:'Baloo 2';font-weight:800;font-size:70px;color:#241C3B;text-align:center;line-height:1}
.pcbar{width:380px;height:32px;border-radius:22px;background:#EDE7DA;overflow:hidden}
.pcfill{height:100%;border-radius:22px}
.pcchip{line-height:0;opacity:0}
.crown{position:absolute;top:-110px;left:50%;transform:translateX(-50%) rotate(-8deg);font-size:100px;z-index:7;filter:drop-shadow(0 8px 12px rgba(0,0,0,.4));opacity:0}
.ribbon{position:absolute;top:-30px;left:50%;transform:translateX(-50%) scale(.6);font-family:'Baloo 2';font-weight:800;font-size:38px;padding:12px 46px;border-radius:999px;letter-spacing:2px;box-shadow:0 8px 16px rgba(0,0,0,.4);z-index:6;white-space:nowrap;border:4px solid #fff;opacity:0}
.foot4{position:absolute;bottom:52px;width:100%;display:flex;align-items:center;justify-content:center;gap:22px;z-index:6}
.foot4 span{font-family:'Baloo 2';font-weight:800;font-size:60px;color:#fff;text-shadow:0 4px 10px rgba(0,0,0,.4)}
#count{position:absolute;top:760px;left:50%;transform:translate(-50%,-50%);width:360px;height:360px;border-radius:50%;background:rgba(255,255,255,.16);border:10px solid #fff;display:flex;align-items:center;justify-content:center;z-index:9;opacity:0}
#count span{font-family:'Luckiest Guy';font-size:250px;color:#fff;-webkit-text-stroke:8px ${P.headStroke};paint-order:stroke fill;line-height:1}
</style></head><body><div class="stage">
  ${suitBg('#fff')}<div class="spot"></div><div class="vig"></div>
  <div class="rail"></div><div class="rail2"></div>
  <div class="plaque"><div class="t">${esc(Q.head)}</div><div class="s" id="sub">${esc(Q.sub)}</div></div>
  <div class="tbl">
    ${cardMarkup('A',IA,Q.sa,Q.la,P.a,Q.fitA)}
    ${cardMarkup('B',IB,Q.sb,Q.lb,P.b,Q.fitB)}
  </div>
  <div id="count"><span>3</span></div>
  <div class="foot4">${deck(80)}<span>DecideDeck</span></div>
</div>
<script>
const WIN=${JSON.stringify(Q.win)}, PA=${Q.pa}, PB=${Q.pb};
const GLOW={A:${JSON.stringify(GLOWA)}, B:${JSON.stringify(GLOWB)}};
const BASE='0 26px 46px rgba(0,0,0,.45)';
const el=id=>document.getElementById(id);
const A=el('A'),B=el('B');
const parts={
  A:{card:A,crown:el('Acrown'),rib:el('Arib'),fill:el('Afill'),chipw:el('Achipwrap'),pct:document.querySelector('#Achip .pct'),base:-4,pctVal:PA},
  B:{card:B,crown:el('Bcrown'),rib:el('Brib'),fill:el('Bfill'),chipw:el('Bchipwrap'),pct:document.querySelector('#Bchip .pct'),base:4,pctVal:PB},
};
const countEl=el('count'),countN=countEl.querySelector('span'),sub=el('sub');
const SUB0=${JSON.stringify(Q.sub)};
const VOTE_END=${(Q.vl||1.8).toFixed(2)},STEP=0.55,REVEAL=VOTE_END+3*STEP,beats=[VOTE_END,VOTE_END+STEP,VOTE_END+2*STEP];
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const ease=x=>x<0?0:x>1?1:(1-Math.cos(Math.PI*x))/2;
const easeOut=x=>x<0?0:x>1?1:1-Math.pow(1-x,3);
const backOut=x=>{if(x<=0)return 0;if(x>=1)return 1;const c1=1.1,c3=c1+1;return 1+c3*Math.pow(x-1,3)+c1*Math.pow(x-1,2);};
function squash(t){let s=0;for(const bt of beats){if(t>=bt){const sb=t-bt;s+=14*Math.exp(-sb/0.16)*(1+Math.cos(2*Math.PI*sb/0.30))/2;}}return s;}

window.setT=function(t){
  const rv=easeOut(clamp((t-REVEAL)/0.55,0,1));
  const riseP=backOut(clamp((t-REVEAL)/0.6,0,1));
  const fillP=easeOut(clamp((t-REVEAL)/0.7,0,1));
  const sq=squash(t);
  const tj=t-REVEAL-0.06;
  const jelly=tj>0?Math.exp(-tj/0.19)*Math.sin(2*Math.PI*tj/0.27):0;
  const idleBob=4*Math.sin(2*Math.PI*t/2.4);

  for(const key of ['A','B']){
    const p=parts[key], sgn=Math.sign(p.base), rock=Math.sin(2*Math.PI*t/3.4+(key==='B'?2:0))*1.2;
    const bob=Math.sin(2*Math.PI*t/2.6+(key==='B'?1.1:0))*10;
    if(WIN===key){
      const rot=(p.base+rock)*(1-rv)+(sgn*1.4)*rv;
      const ty=bob*(1-rv)+(-34)*riseP+idleBob*rv;
      const tx=(-sgn)*(sq*(1-rv)+6*rv);
      const sc=1*(1-riseP)+1.035*riseP;
      const scX=sc*(1+0.032*jelly), scY=sc*(1-0.032*jelly);
      p.card.style.transform='rotate('+rot.toFixed(2)+'deg) translate('+tx.toFixed(1)+'px,'+ty.toFixed(1)+'px) scale('+scX.toFixed(3)+','+scY.toFixed(3)+')';
      p.card.style.boxShadow=rv>0?BASE+','+GLOW[key]:BASE;
      p.card.style.opacity='1'; p.card.style.zIndex=rv>0?4:3;
      const cr=ease(clamp((t-REVEAL-0.05)/0.4,0,1));
      p.crown.style.opacity=cr.toFixed(3);
      p.crown.style.transform='translateX(-50%) rotate(-8deg) translateY('+((1-cr)*-26).toFixed(1)+'px)';
      const rb=easeOut(clamp((t-REVEAL-0.12)/0.35,0,1));
      p.rib.style.opacity=rb.toFixed(3);
      p.rib.style.transform='translateX(-50%) scale('+(0.6+0.4*rb+0.08*Math.sin(rb*Math.PI)).toFixed(3)+')';
    } else {
      const rot=p.base+rock, ty=bob+10*rv, tx=(-sgn)*sq;
      p.card.style.transform='rotate('+rot.toFixed(2)+'deg) translate('+tx.toFixed(1)+'px,'+ty.toFixed(1)+'px)';
      p.card.style.boxShadow=BASE; p.card.style.opacity=(1-0.06*rv).toFixed(3); p.card.style.zIndex=2;
      p.crown.style.opacity='0'; p.rib.style.opacity='0';
    }
    p.fill.style.width=(p.pctVal*fillP).toFixed(1)+'%';
    p.pct.textContent=Math.round(p.pctVal*fillP)+'%';
    p.chipw.style.opacity=fillP.toFixed(3);
  }

  if(t>=VOTE_END && t<REVEAL){
    const idx=Math.min(2,Math.floor((t-VOTE_END)/STEP));
    const local=(t-VOTE_END-idx*STEP)/STEP;
    countN.textContent=String(3-idx);
    const pop=1.0+0.5*Math.exp(-local*9);
    const op=local<0.82?Math.min(1,local*8):(1-(local-0.82)/0.18);
    countEl.style.opacity=clamp(op,0,1).toFixed(3);
    countEl.style.transform='translate(-50%,-50%) scale('+pop.toFixed(3)+')';
  } else countEl.style.opacity='0';

  if(t<VOTE_END) sub.textContent=SUB0;
  else if(t<REVEAL) sub.textContent='LOCKING IN…';
  else sub.textContent='THE RESULTS';
};
window.setT(0);
</script></body></html>`;
}

rounds.forEach((q,i)=>{
  fs.writeFileSync(path.join(outdir,'round_'+i+'.html'), build(q));
  console.log('wrote round_'+i+'.html ('+q.pal+', win '+q.win+', vl '+(q.vl||1.8)+')');
});
