import { action, observable } from 'mobx';

class AppStore {
  stores = null;
  constructor(stores) {
    this.stores = stores;
  }

  @observable query = 'CRETE TABLE tweets(id, username, message);';
  @observable list = null;
}

export default AppStore;
