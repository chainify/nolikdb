import { action, observable } from 'mobx';
import getConfig from 'next/config';
import { keyPair } from '@waves/ts-lib-crypto';
import axios from 'axios';
const { publicRuntimeConfig } = getConfig();
const { API_HOST, CLIENT_SEED, ROOT_SEED } = publicRuntimeConfig;

class AppStore {
  stores = null;
  constructor(stores) {
    this.stores = stores;
    this.getTables = this.getTables.bind(this);
    this.getColumns = this.getColumns.bind(this);
  }

  // @observable query = 'CREATE TABLE tweets(id, username, message)';
  // @observable query =
  //   'INSERT INTO tweets(id, username, message) VALUES(1, amrbz, yadda)';
  @observable query = 'SELECT * FROM contacts';
  @observable list = null;
  @observable tables = [];
  @observable columns = [];

  @action
  getTables() {
    const { crypto } = this.stores;
    axios
      .get(`${API_HOST}/api/v1/tables/${keyPair(CLIENT_SEED).publicKey}`, {})
      .then(res => {
        const tables = [];
        for (let i = 0; i < res.data.length; i += 1) {
          const name = crypto.decryptMessage(
            res.data[i].ciphertext,
            keyPair(ROOT_SEED).publicKey,
          );
          const table = {
            name,
            hash: res.data[i].hash,
          };
          tables.push(table);
        }
        this.tables = tables;
        // this.sendCdmStatus = 'success';
      })
      .catch(e => {
        console.log('err', e);
        // this.sendCdmStatus = 'error';
      });
  }

  @action
  getColumns() {
    return new Promise((resolve, reject) => {
      const { crypto } = this.stores;
      axios
        .get(`${API_HOST}/api/v1/columns/${keyPair(CLIENT_SEED).publicKey}`, {})
        .then(res => {
          const columns = [];
          for (let i = 0; i < res.data.length; i += 1) {
            const columnName = crypto.decryptMessage(
              res.data[i].columnCiphertext,
              keyPair(ROOT_SEED).publicKey,
            );
            const tableName = crypto.decryptMessage(
              res.data[i].tableCiphertext,
              keyPair(ROOT_SEED).publicKey,
            );
            const column = {
              columnName,
              columnHash: res.data[i].columnHash,
              columnCiphertext: res.data[i].columnCiphertext,
              tableName,
              tableHash: res.data[i].tableHash,
              tableCiphertext: res.data[i].tableCiphertext,
            };
            columns.push(column);
          }

          resolve(columns);
          // this.sendCdmStatus = 'success';
        })
        .catch(e => {
          console.log('err', e);
          reject(e);
          // this.sendCdmStatus = 'error';
        });
    });
  }

  @action
  getValues() {
    return new Promise((resolve, reject) => {
      const { crypto } = this.stores;
      axios
        .get(`${API_HOST}/api/v1/values/${keyPair(CLIENT_SEED).publicKey}`, {})
        .then(res => {
          const values = [];
          for (let i = 0; i < res.data.length; i += 1) {
            const columnName = crypto.decryptMessage(
              res.data[i].columnCiphertext,
              keyPair(ROOT_SEED).publicKey,
            );

            const valueName = crypto.decryptMessage(
              res.data[i].valueCiphertext,
              keyPair(ROOT_SEED).publicKey,
            );

            const value = {
              columnName,
              columnHash: res.data[i].columnHash,
              columnCiphertext: res.data[i].columnCiphertext,
              valueName,
              valueHash: res.data[i].valueHash,
              valueCiphertext: res.data[i].valueCiphertext,
            };
            values.push(value);
          }

          resolve(values);
          // this.sendCdmStatus = 'success';
        })
        .catch(e => {
          console.log('err', e);
          reject(e);
          // this.sendCdmStatus = 'error';
        });
    });
  }
}

export default AppStore;
