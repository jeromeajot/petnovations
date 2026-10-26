/*
 * frida_dump_key.js
 *
 * Captures the CatGenie API signing key by hooking the moment the app computes
 * a signature, rather than digging it out of the keychain.
 *
 * The app signs requests with HMAC-SHA256. On the Apple-Silicon (iOS-on-Mac)
 * runtime that call goes through Apple's CommonCrypto CCHmac / CCHmacInit. The
 * `key` argument to those functions IS the signing key we need, already in its
 * final derived form. We also hook CCCrypt to confirm the AES key used for the
 * x-pm-en-dec header (optional, we already know it).
 *
 * Usage (see EXTRACTION.md for the full procedure):
 *     frida -n CatGenie -l frida_dump_key.js
 * then do something in the app that triggers a network call (pull to refresh).
 *
 * HMAC-SHA256 == kCCHmacAlgSHA256 == 2
 * HMAC-SHA1   == 1   (ignored)
 */

'use strict';

const SEEN = new Set();

function describe(ptrVal, len) {
  if (ptrVal.isNull() || len.toInt32() <= 0) return '(empty)';
  const n = Math.min(len.toInt32(), 128);
  const bytes = ptrVal.readByteArray(n);
  const u8 = new Uint8Array(bytes);
  let ascii = '';
  let printable = true;
  for (let i = 0; i < u8.length; i++) {
    const c = u8[i];
    if (c >= 0x20 && c <= 0x7e) {
      ascii += String.fromCharCode(c);
    } else {
      ascii += '.';
      printable = false;
    }
  }
  let hex = '';
  for (let i = 0; i < u8.length; i++) hex += ('0' + u8[i].toString(16)).slice(-2);
  return (printable ? `ascii="${ascii}"` : `(binary) ascii~="${ascii}"`) +
         `  len=${len.toInt32()}  hex=${hex}`;
}

function report(tag, keyPtr, keyLen) {
  const info = describe(keyPtr, keyLen);
  const dedup = tag + '|' + info;
  if (SEEN.has(dedup)) return;
  SEEN.add(dedup);
  console.log('\n========================================');
  console.log(`[${tag}] HMAC-SHA256 key observed:`);
  console.log('  ' + info);
  console.log('========================================\n');
}

function hookHmac() {
  const ccHmac = Module.findExportByName(null, 'CCHmac');
  if (ccHmac) {
    // void CCHmac(CCHmacAlgorithm algorithm, const void *key, size_t keyLength,
    //             const void *data, size_t dataLength, void *macOut)
    Interceptor.attach(ccHmac, {
      onEnter(args) {
        if (args[0].toInt32() === 2) {
          report('CCHmac', args[1], args[2]);
        }
      },
    });
    console.log('[+] Hooked CCHmac');
  } else {
    console.log('[-] CCHmac not found');
  }

  const ccHmacInit = Module.findExportByName(null, 'CCHmacInit');
  if (ccHmacInit) {
    // void CCHmacInit(CCHmacContext *ctx, CCHmacAlgorithm algorithm,
    //                 const void *key, size_t keyLength)
    Interceptor.attach(ccHmacInit, {
      onEnter(args) {
        if (args[1].toInt32() === 2) {
          report('CCHmacInit', args[2], args[3]);
        }
      },
    });
    console.log('[+] Hooked CCHmacInit');
  } else {
    console.log('[-] CCHmacInit not found');
  }
}

function hookAesConfirm() {
  // Optional: confirm the AES key for x-pm-en-dec. kCCEncrypt=0, kCCAlgorithmAES=0.
  const ccCrypt = Module.findExportByName(null, 'CCCrypt');
  if (!ccCrypt) {
    console.log('[-] CCCrypt not found (AES confirmation skipped)');
    return;
  }
  // CCCryptorStatus CCCrypt(CCOperation op, CCAlgorithm alg, CCOptions options,
  //   const void *key, size_t keyLength, const void *iv,
  //   const void *dataIn, size_t dataInLength, void *dataOut, ...)
  Interceptor.attach(ccCrypt, {
    onEnter(args) {
      if (args[1].toInt32() === 0) {
        const info = describe(args[3], args[4]);
        const dedup = 'CCCrypt|' + info;
        if (!SEEN.has(dedup)) {
          SEEN.add(dedup);
          console.log('\n[CCCrypt AES] key: ' + info + '\n');
        }
      }
    },
  });
  console.log('[+] Hooked CCCrypt (AES confirmation)');
}

console.log('=== CatGenie signing-key dumper ===');
console.log('Trigger a network request in the app (e.g. pull to refresh).');
console.log('The 30-char ascii="..." value under CCHmac is your signing key.\n');
hookHmac();
hookAesConfirm();
