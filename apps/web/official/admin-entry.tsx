import {useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Building2,Search,ShieldCheck,ClipboardCheck} from 'lucide-react';
import SidebarNav from './components/primitives/SidebarNav';
import BusinessWorkspace from './components/business/BusinessWorkspace';
import UserWorkspace from './components/user/UserWorkspace';
import {api,logout} from './api-client.js';

declare global {interface Window {originproofTestApi?:string;selectAction:(key:string,proofId?:string)=>void}}
const sections={business:'기업 기능',personal:'개인 기능',operator:'기관 승인',tests:'검사 결과'};
function Console(){
 const [section,setSection]=useState<keyof typeof sections>(new URLSearchParams(location.search).has('proof_id')?'personal':'business');
 const [account,setAccount]=useState('bank');
 const [action,setAction]=useState('status');
 const [ready,setReady]=useState(false);
 const [error,setError]=useState('');
 useEffect(()=>{void api('/v1/auth/me',undefined,'/api').then(me=>{if(me.role!=='operator')throw new Error('운영자 계정으로 로그인해 주세요.');setReady(true);}).catch(e=>setError(e.message));},[]);
 function choose(next:keyof typeof sections){
  window.originproofTestApi=next==='business'?`/test-api/${account}`:next==='personal'?'/test-api/recipient':'/test-api/operator';
  if(next===section&&(next==='business'||next==='personal'))window.selectAction(next==='business'?'status':'verify');
  setAction(next==='business'?'status':'verify');
  setSection(next);if(next==='operator')window.dispatchEvent(new Event('originproof-operator-refresh'));
 }
 useEffect(()=>()=>{delete window.originproofTestApi;},[]);
 useEffect(()=>{const change=(e:Event)=>setAction((e as CustomEvent).detail.key);window.addEventListener('originproof-action',change);return()=>window.removeEventListener('originproof-action',change);},[]);
 useEffect(()=>{document.getElementById('operator-panel')!.hidden=section!=='operator';document.getElementById('tests-panel')!.hidden=section!=='tests';},[section]);
 return <div className="app"><div id="sidebar-root" className="dark"><SidebarNav fill activeNav={section} newChatLabel="기업 · 개인 테스트" onNewChat={()=>choose('business')} navItems={[
  {key:'business',label:sections.business,icon:<Building2 size={18}/>},
  {key:'personal',label:sections.personal,icon:<Search size={18}/>},
  {key:'operator',label:sections.operator,icon:<ShieldCheck size={18}/>},
  {key:'tests',label:sections.tests,icon:<ClipboardCheck size={18}/>},
 ]} onNavigate={key=>choose(key as keyof typeof sections)} onSignOut={()=>{void logout();}} recents={[]} footerLabel="메인으로" onFooterClick={()=>{location.href='index.html';}}/></div>
 <main className="main"><nav className="console-nav" aria-label="관리자 테스트 메뉴">{Object.entries(sections).map(([key,label])=><button key={key} className={section===key?'active':''} aria-pressed={section===key} onClick={()=>choose(key as keyof typeof sections)}>{label}</button>)}</nav>
 {(section==='business'||section==='personal')&&<nav className="console-actions" aria-label="기능 메뉴">{(section==='business'?[['status','기관 상태'],['keys','공개키 관리'],['issue','Proof 발행'],['proofs','발행 목록'],['operations','작업 이력']]:[['verify','Proof 조회'],['compare','내용 비교'],['consume','요청 사용'],['history','검증 내역']]).map(([key,label])=><button key={key} aria-pressed={action===key} onClick={()=>window.selectAction(key)}>{label}</button>)}</nav>}
 {error?<section className="uw-shell"><p role="alert">{error}</p><a className="uw-secondary" href="user-login.html">로그인</a></section>:!ready?<section className="uw-shell"><p role="status">운영자 계정 확인 중…</p></section>:<>
 {section==='business'&&<><label className="console-account">합성 기관<select aria-label="테스트 기관" value={account} onChange={e=>{window.originproofTestApi=`/test-api/${e.target.value}`;setAction('status');setAccount(e.target.value);}}><option value="bank">Origin Mock Bank</option><option value="office">Origin Mock Office</option></select></label><BusinessWorkspace key={account} lifecycleEnabled apiPrefix={`/test-api/${account}`}/></>}
 {section==='personal'&&<UserWorkspace lifecycleEnabled apiPrefix="/test-api/recipient"/>}
 </>}
 <div ref={node=>{const panels=document.querySelector('.console-panels');if(node&&panels&&panels.parentElement!==node)node.append(panels);}}/></main></div>;
}
window.originproofTestApi=new URLSearchParams(location.search).has('proof_id')?'/test-api/recipient':'/test-api/bank';
window.selectAction=(key,proofId)=>window.dispatchEvent(new CustomEvent('originproof-action',{detail:{key,proofId}}));
createRoot(document.getElementById('admin-root')!).render(<Console/>);
