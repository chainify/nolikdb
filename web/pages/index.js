import React from 'react';
import PropTypes from 'prop-types';
import { observer, inject } from 'mobx-react';
import { Divider, Input, Icon } from 'antd';
import Router from 'next/router';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPaperPlane } from '@fortawesome/free-solid-svg-icons';
import mouseTrap from 'react-mousetrap';

const { TextArea } = Input;

@inject('index', 'cdms')
@observer
class Index extends React.Component {
  componentDidMount() {
    const { cdms } = this.props;
    this.props.bindShortcut('meta+enter', () => {
      cdms.sendQuery();
    });
  }

  render() {
    const { index, cdms } = this.props;
    return (
      <div className="main">
        <div className="form">
          <div className="textArea">
            <TextArea
              placeholder="White your query"
              value={index.query}
              onChange={e => {
                index.query = e.target.value;
              }}
              autosize={{ minRows: 1, maxRows: 12 }}
              autoFocus
              className="mousetrap"
              style={{
                border: 'none',
                background: 'transparent',
                margin: 0,
                padding: '0 0px',
                outline: 'none',
                boxShadow: 'none',
                fontSize: '32px',
                lineHeight: '40px',
                height: '40px',
                resize: 'none',
                caretColor: '#fff',
                color: '#fff',
              }}
              disabled={cdms.sendCdmStatus === 'pending'}
            />
          </div>
          <div className="formButtons">
            <button
              type="button"
              className="paperPlane"
              disabled={
                index.query.trim() === '' || cdms.sendCdmStatus === 'pending'
              }
              onClick={() => {
                cdms.sendQuery();
              }}
            >
              {cdms.sendCdmStatus === 'pending' ? (
                <Icon type="loading" />
              ) : (
                <FontAwesomeIcon icon={faPaperPlane} />
              )}
            </button>
          </div>
        </div>
        <Divider />
        <div className="containter">
          {index.list === null && 'Nothing to display'}
          {index.list &&
            index.list.map(el => (
              <p>
                {el.columnName} &mdash; {el.valueName}
              </p>
            ))}
        </div>
        <style jsx>{`
          .main {
            height: 100vh;
            background: #2196f3;
            color: #fff;
            font-family: 'Montserrat', sans-serif;
            display: flex;
            flex-direction: column;
            padding: 4em 8em;
          }

          .form {
            display: flex;
            flex-direction: row;
            min-height: 60px;
          }

          .textArea {
            max-height: 400px;
            flex-grow: 1;
          }

          .formButtons {
            width: 60px;
            text-align: right;
          }

          .formButtons button {
            border: none;
            background: transparent;
            padding: 0;
            margin: 0 0 6px 0;
            width: 100%;
            text-align: left;
            box-shadow: none;
            outline: 0;
            cursor: pointer;
            height: 40px;
            width: 40px;
            font-size: 40px;
            line-height: 40px;
            text-align: center;
          }

          button.paperPlane {
            color: #fff;
          }

          .formButtons button:disabled {
            color: #ddd;
            cursor: not-allowed;
          }

          .formButtons button:enabled:hover {
            color: #90caf9;
          }

          .containter {
            flex: 1;
          }

        `}</style>
      </div>
    );
  }
}

Index.propTypes = {
  index: PropTypes.object,
  cdms: PropTypes.object,
  bindShortcut: PropTypes.func,
};

export default mouseTrap(Index);
