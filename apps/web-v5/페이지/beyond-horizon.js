// Beyond Horizon WebGL background (ported from the supplied Originkit component).
const horizonCanvas=document.querySelector("#beyond-horizon-canvas");
const horizonVert=`attribute vec2 aPos;
varying vec2 vUv;
void main() {
  vUv = aPos * 0.5 + 0.5;
  gl_Position = vec4(aPos, 0.0, 1.0);
}`;
const horizonFrag=`precision highp float;

varying vec2 vUv;

uniform vec2  uRes;
uniform float uTime;
uniform vec2  uMouse;
uniform float uHover;
uniform float uBright;
uniform float uHorizonY;
uniform float uHorizonR;
uniform float uHaze;
uniform float uCoreSize;
uniform float uCoreHover;
uniform float uRimSpread;
uniform float uParallax;
uniform float uFit;
uniform vec3  uBg;
uniform vec3  uCore;
uniform vec3  uMid;
uniform vec3  uDeep;
uniform float uLight;   // 5안 밝은 모드: 1이면 같은 빛을 밝은 바탕 위 보라색으로
uniform vec3  uLightBg;
uniform float uStreak;  // 가로로 퍼지는 빛줄기(렌즈 플레어) 세기

const int STEPS = 26;
const float REF_ASPECT = 0.459091;

float hash31(vec3 p) {
  p = fract(p * 0.1031);
  p += dot(p, p.yzx + 33.33);
  return fract((p.x + p.y) * p.z);
}

float vnoise(vec3 x) {
  vec3 i = floor(x);
  vec3 f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  float n000 = hash31(i);
  float n100 = hash31(i + vec3(1.0, 0.0, 0.0));
  float n010 = hash31(i + vec3(0.0, 1.0, 0.0));
  float n110 = hash31(i + vec3(1.0, 1.0, 0.0));
  float n001 = hash31(i + vec3(0.0, 0.0, 1.0));
  float n101 = hash31(i + vec3(1.0, 0.0, 1.0));
  float n011 = hash31(i + vec3(0.0, 1.0, 1.0));
  float n111 = hash31(i + vec3(1.0, 1.0, 1.0));
  return mix(
    mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y),
    mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y),
    f.z);
}

float fbm(vec3 p) {
  float s = 0.0;
  float a = 0.5;
  for (int i = 0; i < 4; i++) {
    s += a * vnoise(p);
    p = p * 2.02;
    p.xz = mat2(0.80, 0.60, -0.60, 0.80) * p.xz;
    a *= 0.5;
  }
  return s;
}

float hash21(vec2 p) {
  vec3 q = fract(vec3(p.xyx) * 0.1031);
  q += dot(q, q.yzx + 33.33);
  return fract((q.x + q.y) * q.z);
}

vec3 tonemapTanh(vec3 x) {
  x = clamp(x, -12.0, 12.0);
  vec3 e2 = exp(2.0 * x);
  return (e2 - 1.0) / (e2 + 1.0);
}

void main() {
  float aspect = uRes.y / uRes.x;

  vec2 uv = vec2(vUv.x, 1.0 - vUv.y);

  float unit = clamp(pow(max(aspect, 0.0001) / REF_ASPECT, uFit), 0.45, 3.2);
  float inv = 1.0 / unit;

  vec2 P = vec2(uv.x - 0.5, (uv.y - uHorizonY) * aspect) * inv;

  float pxUnit = inv / max(uRes.x, 1.0);

  float hv = clamp(uHover, 0.0, 1.0);

  vec2 m = uMouse * hv * uParallax * inv;

  float coreSize  = mix(uCoreSize, uCoreHover, hv);
  float rimSpread = mix(uRimSpread, 0.220, hv);
  float rimGain   = mix(0.55, 1.9, hv);
  float hazeGain  = mix(1.15, 9.00, hv);
  float hazeK     = mix(20.0, 19.0, hv);
  float hazeCut0  = mix(0.21, 0.40, hv);
  float hazeCut1  = mix(0.13, 0.28, hv);

  vec3 col = uBg;

  vec2 corePos = vec2(m.x * 0.015, m.y * 0.007);
  float d = length(P - corePos);
  float g = coreSize / max(d, 0.0009);
  g = mix(g, g * g, 0.55);

  g *= mix(1.0, smoothstep(0.46, 0.28, d), hv);
  g *= uBright;

  vec3 glowCol = mix(uDeep, uMid, clamp(g * 2.4, 0.0, 1.0));
  glowCol = mix(glowCol, uCore, clamp((g - 0.30) * 1.7, 0.0, 1.0));
  col += glowCol * g;

  vec3 ro = vec3(0.0, 0.0, -1.6);
  vec3 rd = normalize(vec3(P - corePos, 1.2));
  float t = 0.28;
  float stepSize = 0.085;
  float trans = 1.0;
  vec3 haze = vec3(0.0);
  vec2 drift = m * 0.16;

  for (int i = 0; i < STEPS; i++) {
    if (trans < 0.02) break;
    vec3 pos = ro + rd * t;

    vec3 q = pos * vec3(3.2, 1.75, 3.2);
    q.y -= uTime * 0.10;
    q.z += uTime * 0.035;
    q.xy += drift;

    float dens = fbm(q);
    dens = smoothstep(0.47, 0.83, dens);

    float dl = length(pos.xy * vec2(1.0, 0.72));
    float li = 1.0 / (1.0 + dl * dl * 110.0);

    vec3 lc = mix(uDeep, uMid, clamp(li * 1.6, 0.0, 1.0));
    lc += vec3(0.16, 0.05, -0.04) * (1.0 - dens) * li * 0.5;

    haze += dens * li * lc * trans * stepSize;
    trans *= 1.0 - dens * 0.28;
    t += stepSize;
  }

  float hazeEnv = exp(-d * hazeK) * smoothstep(hazeCut0, hazeCut1, d);
  col += haze * uHaze * hazeEnv * hazeGain;

  float discD = length(P - vec2(corePos.x, uHorizonR)) - uHorizonR;
  float aa = 1.4 * pxUnit;
  float above = smoothstep(-aa, aa, discD);

  float rimDx = abs(P.x - corePos.x);

  float rimBase = exp(-rimDx / max(rimSpread, 0.001));
  rimBase *= mix(1.0, smoothstep(0.40, 0.26, rimDx), hv);

  float rimFall = rimBase * mix(1.0, mix(0.22, 1.0, smoothstep(0.0, 0.18, rimDx)), hv);

  float kMax = 0.7 / max(pxUnit, 1e-7);

  float shade = exp(min(discD, 0.0) * min(340.0, kMax));
  float bleed = exp(min(discD, 0.0) * min(95.0, kMax)) * rimBase * hv * 0.85;
  vec3 ground = uBg * (1.0 - 0.85 * clamp(shade, 0.0, 1.0)) + uMid * bleed;
  col = mix(ground, col, above);

  float rimThin  = exp(-abs(discD) * min(mix(620.0, 150.0, hv), kMax));
  float rimBroad = exp(-abs(discD) * min(mix(620.0, 22.0, hv), kMax));
  float rimBand  = rimThin + mix(0.0, 0.26, hv) * rimBroad;
  col += uMid * rimBand * rimFall * rimGain * above * uBright;

  col = tonemapTanh(col);
  if (uLight > 0.0) {
    // 어두운 바탕에서 계산한 빛의 세기를 밝은 바탕 위 보라색 농도로 바꾼다(흰 바탕에 흰 빛은 안 보이므로)
    float a = clamp(max(col.r, max(col.g, col.b)), 0.0, 1.0);
    vec2 sp = P - corePos;
    float streak = exp(-abs(sp.y) * 70.0) * exp(-abs(sp.x) * 2.2) + 0.5 * exp(-abs(sp.y) * 18.0) * exp(-abs(sp.x) * 5.0);
    a = clamp(a + streak * uStreak * (0.55 + 0.45 * hv), 0.0, 1.0);
    vec3 tint = mix(uMid, uDeep, smoothstep(0.45, 1.0, a));
    col = mix(uLightBg, tint, a * uLight);
  }
  col += (hash21(gl_FragCoord.xy) - 0.5) / 255.0;

  gl_FragColor = vec4(col, 1.0);
}`;
const horizonDefaults={background:"#08080A",coreColor:"#FFFFFF",midColor:"#B79BFA",deepColor:"#3A2A78",brightness:2,coreSize:.02,coreHover:.04,haze:3,speed:1,parallax:3,fit:50,horizonY:.8025,horizonRadius:1.867,rimSpread:.035};
function horizonRgb(hex){const n=parseInt(hex.slice(1),16);return [((n>>16)&255)/255,((n>>8)&255)/255,(n&255)/255]}
function horizonShader(gl,type,source){const shader=gl.createShader(type);if(!shader)return null;gl.shaderSource(shader,source);gl.compileShader(shader);if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS)){console.warn("Beyond Horizon shader unavailable:",gl.getShaderInfoLog(shader));gl.deleteShader(shader);return null}return shader}
function startBeyondHorizon(){
  if(!horizonCanvas)return;
  const gl=horizonCanvas.getContext("webgl",{antialias:false,alpha:false,powerPreference:"high-performance"});
  if(!gl){horizonCanvas.style.display="none";return}
  const vs=horizonShader(gl,gl.VERTEX_SHADER,horizonVert),fs=horizonShader(gl,gl.FRAGMENT_SHADER,horizonFrag);if(!vs||!fs){horizonCanvas.style.display="none";return}
  const program=gl.createProgram();if(!program){horizonCanvas.style.display="none";return}gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS)){console.warn("Beyond Horizon program unavailable:",gl.getProgramInfoLog(program));horizonCanvas.style.display="none";return}gl.useProgram(program);
  const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);const pos=gl.getAttribLocation(program,"aPos");gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,2,gl.FLOAT,false,0,0);
  const names={res:"uRes",time:"uTime",mouse:"uMouse",hover:"uHover",bright:"uBright",horizonY:"uHorizonY",horizonR:"uHorizonR",haze:"uHaze",coreSize:"uCoreSize",coreHover:"uCoreHover",rimSpread:"uRimSpread",parallax:"uParallax",fit:"uFit",bg:"uBg",core:"uCore",mid:"uMid",deep:"uDeep",light:"uLight",lightBg:"uLightBg",streak:"uStreak"},u=Object.fromEntries(Object.entries(names).map(([key,name])=>[key,gl.getUniformLocation(program,name)]));
  const pointer={x:0,y:0,targetX:0,targetY:0,hover:0,targetHover:0},colors={bg:horizonRgb(horizonDefaults.background),core:horizonRgb(horizonDefaults.coreColor),mid:horizonRgb(horizonDefaults.midColor),deep:horizonRgb(horizonDefaults.deepColor)};
  // 5안 밝은 모드 색: 바탕은 계산용 검정, 빛은 보라 계열, 화면 바탕은 연한 흰색
  // 밝은 모드 빛 색 후보(주소 ?glow= 로 비교용, 기본은 purple)
  const glowSets={purple:["#8C70CE","#5B3FB5","#F6F5F9",.92],blue:["#5B8DEF","#2A5FD0","#F5F7FC",.85],teal:["#3FB8A8","#15857A","#F4F8F7",.8],gold:["#E8B04A","#B9800F","#FBF8F1",.85],lavender:["#B8A8F0","#8F7CDB","#F7F6FB",.7],bluepurple:["#7A8CFF","#7B4FE0","#F6F6FC",.85],sun:["#E5392A","#FF9F1C","#FBF5F0",.95],flare:["#D8AE5E","#FFF8E6","#E9E6E0",.97,1]};  // flare: 금빛 바깥 + 크림빛 흰 가운데 + 가로 빛줄기  // sun: 바깥은 붉은 노을, 가운데는 주황·금빛 태양
  const pick=(new URLSearchParams(location.search).get("glow"))||"sun",gs=glowSets[pick]||glowSets.purple;
  const lightColors={bg:[0,0,0],core:horizonRgb(gs[0]),mid:horizonRgb(gs[0]),deep:horizonRgb(gs[1]),page:horizonRgb(gs[2]),strength:gs[3],streak:gs[4]||0};const isLight=()=>document.documentElement.dataset.theme==="light";let width=0,height=0,raf=0,start=0,lastTime=0;const reduced=window.matchMedia("(prefers-reduced-motion: reduce)");
  function resize(){const rect=horizonCanvas.getBoundingClientRect(),dpr=Math.min(window.devicePixelRatio||1,2),scale=Math.max(.6*dpr,1);let w=Math.max(2,Math.round(rect.width*scale)),h=Math.max(2,Math.round(rect.height*scale));const over=w*h/2200000;if(over>1){const fit=Math.sqrt(1/over);w=Math.max(2,Math.round(w*fit));h=Math.max(2,Math.round(h*fit))}if(w===width&&h===height)return false;width=w;height=h;horizonCanvas.width=w;horizonCanvas.height=h;gl.viewport(0,0,w,h);return true}
  function draw(time){const p=pointer,d=horizonDefaults;gl.uniform2f(u.res,width,height);gl.uniform1f(u.time,time*d.speed);gl.uniform2f(u.mouse,p.x,p.y);gl.uniform1f(u.hover,p.hover);gl.uniform1f(u.bright,d.brightness);gl.uniform1f(u.horizonY,d.horizonY);gl.uniform1f(u.horizonR,d.horizonRadius);gl.uniform1f(u.haze,d.haze);gl.uniform1f(u.coreSize,d.coreSize);gl.uniform1f(u.coreHover,d.coreHover);gl.uniform1f(u.rimSpread,d.rimSpread);gl.uniform1f(u.parallax,d.parallax);gl.uniform1f(u.fit,d.fit/100);const c=isLight()?lightColors:colors;gl.uniform3fv(u.bg,c.bg);gl.uniform3fv(u.core,c.core);gl.uniform3fv(u.mid,c.mid);gl.uniform3fv(u.deep,c.deep);gl.uniform1f(u.light,isLight()?lightColors.strength:0);gl.uniform3fv(u.lightBg,lightColors.page);gl.uniform1f(u.streak,isLight()?lightColors.streak:0);gl.drawArrays(gl.TRIANGLES,0,3)}
  function frame(now){if(!start)start=now;lastTime=(now-start)/1000;pointer.x+=(pointer.targetX-pointer.x)*.06;pointer.y+=(pointer.targetY-pointer.y)*.06;pointer.hover+=(pointer.targetHover-pointer.hover)*.05;draw(reduced.matches?0:lastTime);if(!reduced.matches)raf=requestAnimationFrame(frame)}
  function updatePointer(event){const rect=horizonCanvas.getBoundingClientRect();if(!rect.width||!rect.height)return;pointer.targetX=(event.clientX-rect.left)/rect.width-.5;pointer.targetY=(event.clientY-rect.top)/rect.height-.7055;pointer.targetHover=1}
  function clearPointer(){pointer.targetX=0;pointer.targetY=0;pointer.targetHover=0}
  horizonCanvas.parentElement.addEventListener("pointermove",updatePointer);horizonCanvas.parentElement.addEventListener("pointerenter",updatePointer);horizonCanvas.parentElement.addEventListener("pointerleave",clearPointer);
  new MutationObserver(()=>draw(lastTime)).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});
  const observer=new ResizeObserver(()=>{if(resize())draw(lastTime)});observer.observe(horizonCanvas);resize();draw(0);if(!reduced.matches)raf=requestAnimationFrame(frame);
}
startBeyondHorizon();
