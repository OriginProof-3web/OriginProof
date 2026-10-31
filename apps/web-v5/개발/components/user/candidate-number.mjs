// 사용자가 넣은 금액·버전 글자를 정수로 바꾼다. 쉼표와 끝의 '원'은 허용하고, 그 밖의 글자는 null(비교에서 몰래 빠지지 않게 오류로 알림).
export function parseWholeNumber(value) {
  const text = String(value).trim().replace(/원$/, "").trim().replace(/,/g, "");
  if (!/^[0-9]+$/.test(text)) return null;
  const number = Number(text);
  return Number.isSafeInteger(number) ? number : null;
}
