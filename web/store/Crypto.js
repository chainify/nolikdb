import { action, toJS } from 'mobx';
import { sha256 } from 'js-sha256';
import {
  keyPair,
  messageEncrypt,
  messageDecrypt,
  sharedKey,
  base58Encode,
} from '@waves/ts-lib-crypto';

import getConfig from 'next/config';
const { publicRuntimeConfig } = getConfig();
const {
  CDM_VERSION,
  CLIENT_PREFIX,
  NETWORK,
  ROOT_SEED,
  CLIENT_SEED,
} = publicRuntimeConfig;

class CryptoStore {
  stores = null;
  constructor(stores) {
    this.stores = stores;
    this.wrapCdm = this.wrapCdm.bind(this);
    this.decryptMessage = this.decryptMessage.bind(this);
  }

  @action
  wrapCdm(operations) {
    let cdm = '<?xml version="1.0"?>';
    cdm += '\r\n<cdm>';
    cdm += `\r\n<version>${CDM_VERSION}</version>`;
    cdm += '\r\n<blockchain>Waves</blockchain>';
    cdm += `\r\n<network>${NETWORK.substring(
      0,
      1,
    ).toUpperCase()}${NETWORK.substring(1).toLowerCase()}</network>`;
    cdm += '\r\n<operations>';
    cdm += operations;
    cdm += '\r\n</operations>';
    cdm += '\r\n</cdm>';
    return cdm;
  }

  @action
  randomize(message) {
    const { utils } = this.stores;
    if (!message) return null;
    return `${message}@${sha256(utils.generateRandom(64))}`;
  }

  @action
  encrypt(fromSeed, toSeed, text) {
    let msg = '';
    const messageHash = sha256(text);
    const cipherBytes = messageEncrypt(
      sharedKey(
        keyPair(fromSeed).privateKey,
        keyPair(toSeed).publicKey,
        CLIENT_PREFIX,
      ),
      text,
    );
    const cipherText = base58Encode(cipherBytes);

    msg += `\r\n<ciphertext>${cipherText}</ciphertext>`;
    msg += `\r\n<sha256>${messageHash}</sha256>`;

    return msg;
  }

  // @action
  // block(subject, message, recipient, type) {
  //   let msg = '';
  //   if (subject) {
  //     const sbj = this.encrypt(recipient, subject);
  //     msg += `\r\n<subject>`;
  //     msg += sbj;
  //     msg += `\r\n</subject>`;
  //   }

  //   const body = this.encrypt(recipient, message);
  //   msg += `\r\n<${type}>`;
  //   msg += `\r\n<publickey>${recipient}</publickey>`;
  //   msg += `\r\n</${type}>`;
  //   msg += `\r\n<body>`;
  //   msg += body;
  //   msg += `\r\n</body>`;

  //   return msg;
  // }

  @action
  operation(data) {
    const { origins } = data;
    let op = '';
    if (data.create) {
      const table = this.encrypt(ROOT_SEED, CLIENT_SEED, data.create.table);
      op += '\r\n<create>';
      op += '\r\n<table>';
      op += table;
      op += '\r\n</table>';
      op += '\r\n<columns>';

      for (let i = 0; i < data.create.columns.length; i += 1) {
        const col = this.encrypt(
          ROOT_SEED,
          // data.create.columns[i].seed,
          CLIENT_SEED,
          data.create.columns[i].name,
        );
        op += '\r\n<column>';
        op += col;
        op += '\r\n</column>';
      }

      op += '\r\n</columns>';
      op += '\r\n<origin>';
      op += `\r\n<publickey>${keyPair(ROOT_SEED).publicKey}</publickey>`;
      op += `\r\n<signature>signature</signature>`;
      op += '\r\n</origin>';
      op += '\r\n<recipient>';
      op += `\r\n<publickey>${keyPair(CLIENT_SEED).publicKey}</publickey>`;
      op += '\r\n</recipient>';
      op += '\r\n</create>';
    }

    if (data.insert) {
      op += '\r\n<insert>';
      op += '\r\n<table>';
      op += `\r\n<ciphertext>${data.insert.data[0].table.ciphertext}</ciphertext>`;
      op += `\r\n<sha256>${data.insert.data[0].table.hash}</sha256>`;
      op += '\r\n</table>';
      op += '\r\n<columns>';

      for (let i = 0; i < data.insert.data.length; i += 1) {
        const val = this.encrypt(
          ROOT_SEED,
          CLIENT_SEED,
          data.insert.data[i].value,
        );
        op += '\r\n<column>';
        op += `\r\n<ciphertext>${data.insert.data[i].column.ciphertext}</ciphertext>`;
        op += `\r\n<sha256>${data.insert.data[i].column.hash}</sha256>`;
        op += '\r\n<value>';
        op += val;
        op += '\r\n</value>';
        op += '\r\n</column>';
      }

      op += '\r\n</columns>';
      op += '\r\n<origin>';
      op += `\r\n<publickey>${keyPair(ROOT_SEED).publicKey}</publickey>`;
      op += `\r\n<signature>signature</signature>`;
      op += '\r\n</origin>';
      op += '\r\n<recipient>';
      op += `\r\n<publickey>${keyPair(CLIENT_SEED).publicKey}</publickey>`;
      op += '\r\n</recipient>';
      op += '\r\n</insert>';
    }
    return op;
  }

  @action
  compose(data) {
    let operations = '';
    for (let i = 0; i < data.length; i += 1) {
      const operation = this.operation(data[i]);
      operations += operation;
    }
    return this.wrapCdm(operations);
  }

  @action
  decryptMessage(cipherText, publicKey) {
    const keys = keyPair(CLIENT_SEED);
    let decryptedMessage;
    try {
      decryptedMessage = messageDecrypt(
        sharedKey(keys.privateKey, publicKey, CLIENT_PREFIX),
        cipherText,
      );
    } catch (err) {
      decryptedMessage = '⚠️ Decoding error';
    }
    return decryptedMessage;
  }

  @action
  decryptCdm(cdm) {
    const thisCdm = cdm;

    if (cdm.subject) {
      const subject = this.decryptMessage(
        cdm.subject,
        cdm.direction === 'outgoing' ? cdm.recipient : cdm.logicalSender,
      );
      thisCdm.rawSubject = subject;
      thisCdm.subject = subject.replace(/@[\w]{64}$/gim, '');
    }

    if (cdm.message) {
      const message = this.decryptMessage(
        cdm.message,
        cdm.direction === 'outgoing' ? cdm.recipient : cdm.logicalSender,
      );
      thisCdm.rawMessage = message;
      thisCdm.message = message.replace(/@[\w]{64}$/gim, '');
    }

    return thisCdm;
  }

  @action
  decrypThread(item) {
    const cdms = [];
    const thisItem = item;

    for (let i = 0; i < item.cdms.length; i += 1) {
      const cdm = this.decryptCdm(item.cdms[i]);
      cdms.push(cdm);
    }

    thisItem.cdms = cdms.reverse();
    return thisItem;
  }
}

export default CryptoStore;
