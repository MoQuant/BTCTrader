import React from 'react'
import Plot from 'react-plotly.js'

class CustomWebSocket extends WebSocket {
  constructor(url, protocols, options) {
    options = { ...options, rejectUnauthorized: false };
    super(url, protocols, options);
  }
}

export default class App extends React.Component {
  constructor() {
    super();
    this.state = {
      logger: 'Welcome',
      prices: [0, 0, 0, 0, 0, 0],
      book: null,
      profit: null
    };
    this.plotProfit = this.plotProfit.bind(this);
  }

  componentDidMount() {
    const socket = new CustomWebSocket('wss://tradingsystemserver-534091687193.europe-west1.run.app');
    socket.onmessage = (evt) => {
      const resp = JSON.parse(evt.data);
      this.setState({
        prices: resp['prices'],
        logger: resp['logger'],
        profit: resp['profit'],
        book: resp['book']
      });
    };
  }

  plotProfit() {
    const { profit, book } = this.state;
    const hold = [];

    const layoutBase = {
      font: { color: '#D0D0D0' },
      paper_bgcolor: 'black',
      plot_bgcolor: 'black',
      xaxis: { color: '#D0D0D0' },
      yaxis: { color: '#D0D0D0' },
      width: 400,
      height: 250,
      tickformat: ".6f"
    };

    if (profit && book) {
      hold.push(
        <Plot
          data={[{
            x: profit['x'],
            y: profit['y'],
            type: 'scatter',
            mode: 'lines',
            line: { color: '#00BFFF', width: 3 }
          }]}
          layout={{
            ...layoutBase,
            title: { text: 'Bitcoin Profits' }
          }}
        />
      );

      hold.push(
        <Plot
          data={[{
            x: profit['y'],
            type: 'histogram',
            marker: {
              color: '#00CED1',
              line: { color: '#2F4F4F', width: 2 }
            }
          }]}
          layout={{
            ...layoutBase,
            title: { text: 'Profit Distribution' }
          }}
        />
      );

      hold.push(
        <Plot
          data={[{
            x: book['bp'],
            y: book['bv'],
            type: 'bar',
            marker: { color: '#B22222' }
          }]}
          layout={{
            ...layoutBase,
            title: { text: 'Bid Book' }
          }}
        />
      );

      hold.push(
        <Plot
          data={[{
            x: book['ap'],
            y: book['av'],
            type: 'bar',
            marker: { color: '#4682B4' }
          }]}
          layout={{
            ...layoutBase,
            title: { text: 'Ask Book' }
          }}
        />
      );
    }

    return hold;
  }

  render() {
    const { prices, logger } = this.state;

    //'linear-gradient(145deg, #3c3c3c, #1f1f1f)'

    const chromePanel = {
      background: 'black',
      border: '1px solid #777',
      borderRadius: '15px',
      padding: '20px',
      boxShadow: '0 0 10px #666',
      color: '#D0D0D0',
      maxWidth: '1100px',
      margin: 'auto'
    };

    const headerStyle = {
      fontSize: '40px',
      color: '#E0E0E0',
      textShadow: '0 0 5px #aaa'
    };

    const tableStyle = {
      width: '100%',
      marginTop: '20px',
      borderCollapse: 'collapse',
      textAlign: 'center'
    };

    const rowHead = {
      fontSize: '20px',
      color: '#ccc',
      borderBottom: '1px solid #444',
      paddingBottom: '10px'
    };

    const rowData = {
      fontSize: '22px',
      color: '#00FFFF',
      paddingTop: '10px'
    };

    return (
      <center>
      <div style={{ backgroundColor: '#121212', minHeight: '100vh', padding: '30px' }}>
        <div style={chromePanel}>
          <div style={headerStyle}>🚀 Bitcoin Trader</div>

          <table style={tableStyle}>
            <thead>
              <tr>
                <td style={rowHead}>Price</td>
                <td style={rowHead}>HighBid</td>
                <td style={rowHead}>LowAsk</td>
                <td style={rowHead}>BookRatio</td>
                <td style={rowHead}>Volatility</td>
                <td style={rowHead}>PnL</td>
              </tr>
            </thead>
            <tbody>
              <tr>
                {prices.map((p, i) => (
                  <td key={i} style={rowData}>{p}</td>
                ))}
              </tr>
            </tbody>
          </table>

          <div style={{ marginTop: '30px', fontSize: '20px', color: '#00FA9A' }}>
            {logger}
          </div>

          <div style={{ marginTop: '40px' }}>
            {this.plotProfit()}
          </div>
        </div>
      </div>
      </center>
    );
  }
}
