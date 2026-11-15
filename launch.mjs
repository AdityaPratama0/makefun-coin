// launch.mjs — membuat coin di pump.fun lewat API resmi fun-block.pump.fun
// Pemakaian:
//   node launch.mjs --dry            bangun transaksi, jangan kirim
//   node launch.mjs --send           kirim (butuh SOL di wallet)
//
// Wallet: ~/.agent-sessions/makefun-keypair.json (format solana-keygen, 64 angka)
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { Connection, Keypair, VersionedTransaction } from '@solana/web3.js';

const args = process.argv.slice(2);
const send = args.includes('--send');
const RPC = process.env.RPC_URL || 'https://api.mainnet-beta.solana.com';
const API = 'https://fun-block.pump.fun/agents/create-coin';
const KP = process.env.MAKEFUN_KEYPAIR ||
  `${homedir()}/.agent-sessions/makefun-keypair.json`;

const NAME = process.env.COIN_NAME || 'Make Fun';
const SYMBOL = process.env.COIN_SYMBOL || 'MAKEFUN';
const URI = process.env.COIN_URI || '';
const LAMPORTS = process.env.COIN_BUY_LAMPORTS || '1000000'; // 0,001 SOL

const kp = Keypair.fromSecretKey(Uint8Array.from(JSON.parse(readFileSync(KP, 'utf8'))));
const conn = new Connection(RPC, 'confirmed');

if (!URI) {
  console.error('COIN_URI belum diisi: unggah metadata.json dan logo ke URL publik dulu');
  process.exit(2);
}

const body = {
  user: kp.publicKey.toBase58(),
  name: NAME,
  symbol: SYMBOL,
  uri: URI,
  solLamports: LAMPORTS,
  encoding: 'base64',
  feePayer: kp.publicKey.toBase58(),
  creator: kp.publicKey.toBase58(),
};

const bal = await conn.getBalance(kp.publicKey);
console.log(`wallet ${kp.publicKey.toBase58()} saldo ${bal / 1e9} SOL`);

let json;
const fromFile = args.includes('--from-file') ? args[args.indexOf('--from-file') + 1] : '/tmp/pf_tx.json';
if (readFileSync) {
  const raw = JSON.parse(readFileSync(fromFile, 'utf8'));
  const inner = raw.text ? JSON.parse(raw.text) : raw;
  json = inner.data || inner;
}
const txB64 = json.transaction || json.tx || json.data?.transaction;
if (!txB64) {
  console.error('tidak ada transaksi di jawaban:', JSON.stringify(json).slice(0, 300));
  process.exit(1);
}

const tx = VersionedTransaction.deserialize(Buffer.from(txB64, 'base64'));
// tanda tangan manual: cari indeks wallet kita di staticAccountKeys lalu isi slotnya
{
  const msg = tx.message.serialize();
  const nacl = (await import('tweetnacl')).default;
  const raw = tx.message.serialize();
  const sig = nacl.sign.detached(raw, kp.secretKey);
  const idx = tx.message.staticAccountKeys.findIndex((k) => k.toBase58() === kp.publicKey.toBase58());
  if (idx < 0) { console.error('wallet tidak ada di account keys'); process.exit(1); }
  tx.signatures[idx] = sig;
  console.log('tanda tangan wallet ditempel di slot', idx);
}
console.log(`transaksi ditandatangani, ukuran ${tx.serialize().length} byte`);

const fee = await conn.getFeeForMessage(tx.message);
console.log(`perkiraan biaya jaringan: ${(fee.value || 0) / 1e9} SOL`);

if (!send) {
  console.log('mode kering: tidak dikirim. tambahkan --send untuk mengirim.');
  process.exit(0);
}
const sig = await conn.sendRawTransaction(tx.serialize(), { skipPreflight: false, maxRetries: 3 });
console.log('terkirim, signature:', sig);
const conf = await conn.confirmTransaction(sig, 'confirmed');
console.log('status konfirmasi:', conf.value.err ? `gagal ${JSON.stringify(conf.value.err)}` : 'ok');
