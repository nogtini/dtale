import _ from "lodash";
import numeral from "numeral";
import PropTypes from "prop-types";
import React from "react";

import corrUtils from "./correlationsUtils";

const MAX_LABEL_LEN = 18;

class CorrelationsCell extends React.Component {
  constructor(props) {
    super(props);
    this.renderHeader = this.renderHeader.bind(this);
  }

  renderHeader(title) {
    const { style } = this.props;
    const props = _.size(title) >= MAX_LABEL_LEN ? { title } : {};
    return (
      <div className="headerCell" style={_.assignIn(style, { fontSize: "10px" })} {...props}>
        <div>{_.truncate(title, { length: MAX_LABEL_LEN })}</div>
      </div>
    );
  }

  render() {
    const { columnIndex, rowIndex, style, correlations, columns, col2, hasDate, selectedDate } = this.props;
    if (rowIndex == 0) {
      if (columnIndex == 0) {
        return null;
      }
      return this.renderHeader(_.isNull(col2) ? columns[columnIndex - 1].value : col2.value);
    }
    const row = correlations[rowIndex - 1];
    if (columnIndex == 0) {
      return this.renderHeader(row.column);
    }
    const prop = _.isNull(col2) ? columns[columnIndex - 1].value : col2.value;
    const corrOnItself = row.column === prop || _.isNull(row[prop]);
    const valueStyle = {
      background: corrOnItself ? "rgba(255,255,255,1)" : corrUtils.colorScale(row[prop]),
      textAlign: "center",
    };
    const props = {};
    if (!corrOnItself) {
      if (hasDate) {
        if (this.props.rolling) {
          props.onClick = () => this.props.buildTs([row.column, prop], selectedDate, true, this.props.window);
        } else {
          props.onClick = () => this.props.buildTs([row.column, prop], selectedDate, false);
        }
      } else {
        props.onClick = () => this.props.buildScatter([row.column, prop]);
      }
      valueStyle.cursor = "pointer";
    }
    if (_.get(this.props.selectedCols, "0") === row.column && _.get(this.props.selectedCols, "1") === prop) {
      valueStyle.paddingTop = ".2em";
      return (
        <div className="cell d-inline" style={_.assignIn({}, style, valueStyle)} {...props}>
          <i className="ico-show-chart float-left" />
          <span style={{ marginLeft: "-1em" }}>{corrOnItself ? "N/A" : numeral(row[prop]).format("0.00")}</span>
        </div>
      );
    }
    return (
      <div className="cell" style={_.assignIn({}, style, valueStyle)} {...props}>
        {corrOnItself ? "N/A" : numeral(row[prop]).format("0.00")}
      </div>
    );
  }
}
CorrelationsCell.displayName = "CorrelationsCell";
CorrelationsCell.propTypes = {
  columnIndex: PropTypes.number,
  rowIndex: PropTypes.number,
  style: PropTypes.object,
  correlations: PropTypes.array,
  columns: PropTypes.array,
  hasDate: PropTypes.bool,
  selectedDate: PropTypes.string,
  buildTs: PropTypes.func,
  buildScatter: PropTypes.func,
  col2: PropTypes.object,
  rolling: PropTypes.bool,
  window: PropTypes.number,
  selectedCols: PropTypes.arrayOf(PropTypes.string),
};

export default CorrelationsCell;
