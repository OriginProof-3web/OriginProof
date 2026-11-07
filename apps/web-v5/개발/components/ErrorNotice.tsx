import {errorInfo} from '../api-client.js';
export default function ErrorNotice({error,loginHref,retry}:{error:unknown;loginHref:string;retry?:()=>void}) {
 if(!error)return null;
 const info=errorInfo(error);
 return <div className="uw-error" role="alert"><p>{info.message}</p>{info.code!=='0'&&<small>상태 코드: {info.code}</small>}<div className="uw-actions">{info.login&&<a className="uw-secondary" href={loginHref}>다시 로그인</a>}{info.retryRead&&retry&&<button type="button" className="uw-secondary" onClick={retry}>현재 상태 다시 조회</button>}</div></div>;
}
