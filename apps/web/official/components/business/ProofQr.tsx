/* eslint-disable @next/next/no-img-element -- Static design bundle displays a generated data URL, not a Next image asset. */
import {useEffect,useState} from 'react';
import QRCode from 'qrcode';
import {proofLink} from '../../w3-input.js';

export default function ProofQr({proofId,href}:{proofId:string;href?:string}) {
 const [image,setImage]=useState('');
 const [error,setError]=useState('');
 const link=href??proofLink(proofId,location.href);
 useEffect(()=>{
  let cancelled=false;
  setImage('');setError('');
  QRCode.toDataURL(link,{width:256,margin:4,errorCorrectionLevel:'M',color:{dark:'#08080aff',light:'#ffffffff'}})
   .then(value=>{if(!cancelled)setImage(value);})
   .catch(()=>{if(!cancelled)setError('QR 생성에 실패했습니다. 검증 링크를 사용해 주세요.');});
  return ()=>{cancelled=true;};
 },[link]);
 return <section className="bw-qr" aria-label="공개 검증 QR">
  {error ? <p role="alert">{error}</p> : image ? <><img src={image} width={256} height={256} alt={href?"관리자 Proof 조회 화면으로 이동하는 QR 코드":"공개 Proof 조회 화면으로 이동하는 QR 코드"}/><a className="uw-secondary" href={image} download={`proof-${proofId}.png`}>QR PNG 저장</a></> : <p role="status">QR 생성 중…</p>}
  <p className="uw-note">{href?"관리자 테스트 QR입니다. 관리자 로그인 후 같은 테스트 환경에서 조회합니다.":"QR에는 공개 Proof ID 링크만 포함됩니다. 자료 내용은 별도 권한 확인 후 비교합니다."}</p>
 </section>;
}
