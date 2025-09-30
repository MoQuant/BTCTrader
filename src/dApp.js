import React from 'react'
import Plot from 'react-plotly.js'

class CustomWebSocket extends WebSocket {
  constructor(url, protocols, options) {
    // Disable SSL certificate verification
    options = {
      ...options,
      rejectUnauthorized: false,
    };
    super(url, protocols, options);
  }
}

export default class App extends React.Component {

  constructor(){
    super();
    this.state = {logger: 'Welcome',
                  prices: [0, 0, 0, 0, 0],
                  book: null,
                  profit: null}
    
    this.plotProfit = this.plotProfit.bind(this)
  }

  componentDidMount(){
    const socket = new CustomWebSocket('wss://tradingsystemserver-534091687193.europe-west1.run.app')
    socket.onmessage = (evt) => {
      const resp = JSON.parse(evt.data)
      this.setState({ prices: resp['prices'],
                      logger: resp['logger'],
                      profit: resp['profit'],
                      book: resp['book']
       })
    }
  }

  plotProfit(){
    const { profit, book } = this.state
    const hold = []
    if(profit !== null && book !== null){
      
      hold.push(
        <Plot
            data={[{
              x: profit['x'],
              y: profit['y'],
              type: 'scatter',
              mode: 'lines',
              line: {
                color: 'red'
              }
            }]}
            layout={{
              title: {
                text: 'Bitcoin Profits',
                font: {
                  color: 'limegreen'
                }
              },
              xaxis: {
                color: 'limegreen'
              },
              yaxis: {
                color: 'limegreen'
              },
              paper_bgcolor: 'black',
              plot_bgcolor: 'black'
            }}
        />
      )
      hold.push(
        <Plot
          data={[{
            x: profit['y'],
            type: 'histogram',
            marker: {
              color: 'cyan',
              line: {
                color: 'black',
                width: 3
              }
            }
          }]}
          layout={{
            title: {
              text: 'Profit Distribution',
              font: {
                color: 'limegreen'
              }
            },
            xaxis: {
              color: 'limegreen'
            },
            yaxis: {
              color: 'limegreen'
            },
            paper_bgcolor: 'black',
            plot_bgcolor: 'black'
          }}
        />
      )

      hold.push(
        <Plot
            data={[{
              x: book['bp'],
              y: book['bv'],
              type: 'bar',
              marker: {
                color: 'red'
              }
            }]}
            layout={{
              title: {
                text: 'Bid Book',
                font: {
                  color: 'limegreen'
                }
              },
              xaxis: {
                color: 'limegreen'
              },
              yaxis: {
                color: 'limegreen'
              },
              paper_bgcolor: 'black',
              plot_bgcolor: 'black'
            }}
        />
      )
      hold.push(
        <Plot
            data={[{
              x: book['ap'],
              y: book['av'],
              type: 'bar',
              marker: {
                color: 'teal'
              }
            }]}
            layout={{
              title: {
                text: 'Ask Book',
                font: {
                  color: 'limegreen'
                }
              },
              xaxis: {
                color: 'limegreen'
              },
              yaxis: {
                color: 'limegreen'
              },
              paper_bgcolor: 'black',
              plot_bgcolor: 'black'
            }}
        />
      )
    }
    return hold
  }

  render(){

    const { prices, logger } = this.state 

    return(
      <React.Fragment>
        <center>
          <div style={{backgroundColor: 'black', color: 'limegreen', fontSize: 35}}>Bitcoin Trader</div>
          <br/>
          <table style={{textAlign: 'center'}}>
            <tr style={{color: 'limegreen', fontSize: 25}}>
              <td>Price</td>
              <td>HighBid</td>
              <td>LowAsk</td>
              <td>BookRatio</td>
              <td>Volatility</td>
            </tr>
            <tr style={{color: 'red', fontSize: 25}}>
              <td>{prices[0]}</td>
              <td>{prices[1]}</td>
              <td>{prices[2]}</td>
              <td>{prices[3]}</td>
              <td>{prices[4]}</td>
            </tr>
          </table>
          <br/>
          <div style={{fontSize: 25, color: 'cyan', textAlign: 'center'}}>{logger}</div>
          <br/>
          <br/>
          <div>{this.plotProfit()}</div>
        </center>
      </React.Fragment>
    );
  }

}
