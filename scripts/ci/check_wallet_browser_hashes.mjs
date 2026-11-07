// Node Web Crypto cross-check; this does not exercise a browser wallet or HTTP API.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const golden = JSON.parse(await readFile(new URL('../../fixtures/golden/wallet_contract_v1.json', import.meta.url), 'utf8'));
const encoder = new TextEncoder();
const hash = async (bytes) => '0x' + Buffer.from(await crypto.subtle.digest('SHA-256', bytes)).toString('hex');
// Both templates contain flat primitives already normalized by the shared API model.
const canonical = (content) => JSON.stringify(Object.fromEntries(Object.keys(content).sort().map((key) => [key, content[key]])));

for (const vector of golden.vectors.filter((item) => item.typed_data.primaryType === 'Publish')) {
  const message = vector.typed_data.message;
  const bytes = Buffer.from(vector.original_base64, 'base64');
  const original = JSON.parse(bytes.toString('utf8'));
  assert.equal(await hash(bytes), message.originalHash);
  assert.equal(canonical(vector.protected_content), vector.protected_canonical_utf8);
  assert.equal(await hash(encoder.encode(canonical(vector.protected_content))), message.protectedHash);
  assert.deepEqual(original.content, vector.protected_content);
  for (const [key, signedKey] of [['issuer_id', 'issuerId'], ['doc_key', 'docKey'], ['document_id', 'documentId'], ['version', 'version'], ['issued_at', 'issuedAt'], ['expires_at', 'expiresAt']]) {
    assert.equal(original[key], message[signedKey]);
  }
}
console.log('Node Web Crypto original/protected hash and field cross-check passed for both templates.');
