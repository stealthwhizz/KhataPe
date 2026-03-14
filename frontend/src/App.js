import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import "@/App.css";
import { initStream, subscribeTransactions } from "@/lib/stream";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const POLL_INTERVAL_MS = 5000;

const toNumber = (value) => {
  const num = Number(value);
  return Number.isFinite(num) ? num : 0;
};

const formatCurrency = (value) => `₹${toNumber(value).toFixed(2)}`;

const normalizeFromDb = (tx) => {
  const amount = toNumber(tx?.amount);
  const gst = amount ? Number((amount * 0.18).toFixed(2)) : 0;
  const net = Number((amount + gst).toFixed(2));

  return {
    id: tx?.id || `${tx?.source || "tx"}-${tx?.timestamp || Date.now()}`,
    payer: tx?.payer || "Unknown",
    amount,
    gst,
    net,
    source: tx?.source || "message_text",
    timestamp: tx?.timestamp || new Date().toISOString(),
  };
};

const normalizeFromStream = (tx) => {
  const amount = toNumber(tx?.amount);
  const gst = toNumber(tx?.gst);
  const net = tx?.net !== undefined ? toNumber(tx?.net) : Number((amount + gst).toFixed(2));

  return {
    id: tx?.transaction_id || `${tx?.source || "stream"}-${tx?.timestamp || Date.now()}`,
    payer: tx?.payer || "Unknown",
    amount,
    gst,
    net,
    source: tx?.source || "stream",
    timestamp: tx?.timestamp || new Date().toISOString(),
  };
};

const mergeByIdNewestFirst = (prevRows, incomingRows) => {
  const map = new Map();
  [...incomingRows, ...prevRows].forEach((row) => {
    map.set(row.id, row);
  });

  return [...map.values()]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 100);
};

function App() {
  const [transactions, setTransactions] = useState([]);
  const [streamStatus, setStreamStatus] = useState("connecting");
  const [lastUpdatedAt, setLastUpdatedAt] = useState("");
  const [error, setError] = useState("");

  const fetchTransactions = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/transactions/recent?limit=50`);
      const rows = (response.data?.transactions || []).map(normalizeFromDb);
      setTransactions((prevRows) => mergeByIdNewestFirst(prevRows, rows));
      setLastUpdatedAt(new Date().toISOString());
      setError("");
    } catch (_err) {
      setError("Could not refresh transactions.");
    }
  }, []);

  useEffect(() => {
    fetchTransactions();
    const timer = setInterval(fetchTransactions, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [fetchTransactions]);

  useEffect(() => {
    let cleanup = null;
    let isMounted = true;

    const start = async () => {
      try {
        await initStream();
        if (!isMounted) return;

        setStreamStatus("live");
        cleanup = await subscribeTransactions(
          (tx) => {
            const row = normalizeFromStream(tx);
            setTransactions((prevRows) => mergeByIdNewestFirst(prevRows, [row]));
            setLastUpdatedAt(new Date().toISOString());
          },
          () => {
            if (isMounted) {
              setStreamStatus("polling");
            }
          },
        );
      } catch (_err) {
        if (isMounted) {
          setStreamStatus("polling");
        }
      }
    };

    start();

    return () => {
      isMounted = false;
      if (cleanup) {
        cleanup();
      }
    };
  }, []);

  const statusLabel = useMemo(() => {
    if (streamStatus === "live") return "Live stream connected";
    if (streamStatus === "polling") return "Using 5-second polling fallback";
    return "Connecting to live stream";
  }, [streamStatus]);

  return (
    <div className="app-shell" data-testid="transactions-dashboard-page">
      <header className="topbar" data-testid="transactions-dashboard-header">
        <div>
          <h1 className="title" data-testid="transactions-dashboard-title">GST Transactions</h1>
          <p className="subtitle" data-testid="transactions-dashboard-subtitle">
            Razorpay and WhatsApp transactions stream here in real time.
          </p>
        </div>
        <button
          className="refresh-button"
          onClick={fetchTransactions}
          data-testid="transactions-refresh-button"
        >
          Refresh now
        </button>
      </header>

      <section className="status-row" data-testid="transactions-status-row">
        <div className="pill" data-testid="transactions-stream-status">
          <span className={`dot ${streamStatus}`} data-testid="transactions-stream-status-dot" />
          <span data-testid="transactions-stream-status-text">{statusLabel}</span>
        </div>
        <div className="pill" data-testid="transactions-last-updated-pill">
          <span data-testid="transactions-last-updated-text">
            Last updated: {lastUpdatedAt ? new Date(lastUpdatedAt).toLocaleTimeString() : "-"}
          </span>
        </div>
      </section>

      {error ? (
        <div className="error-banner" data-testid="transactions-error-banner">{error}</div>
      ) : null}

      <div className="table-wrap" data-testid="transactions-table-wrap">
        <table className="table" data-testid="transactions-table">
          <thead>
            <tr>
              <th data-testid="transactions-table-head-payer">Payer</th>
              <th data-testid="transactions-table-head-amount">Amount</th>
              <th data-testid="transactions-table-head-gst">GST</th>
              <th data-testid="transactions-table-head-net">Net</th>
              <th data-testid="transactions-table-head-source">Source</th>
              <th data-testid="transactions-table-head-time">Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {transactions.length ? (
              transactions.map((tx) => (
                <tr key={tx.id} data-testid={`transactions-row-${tx.id}`}>
                  <td data-testid={`transactions-row-payer-${tx.id}`}>{tx.payer}</td>
                  <td data-testid={`transactions-row-amount-${tx.id}`}>{formatCurrency(tx.amount)}</td>
                  <td data-testid={`transactions-row-gst-${tx.id}`}>{formatCurrency(tx.gst)}</td>
                  <td data-testid={`transactions-row-net-${tx.id}`}>{formatCurrency(tx.net)}</td>
                  <td data-testid={`transactions-row-source-${tx.id}`}>{tx.source}</td>
                  <td data-testid={`transactions-row-time-${tx.id}`}>
                    {new Date(tx.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))
            ) : (
              <tr data-testid="transactions-empty-row">
                <td colSpan={6} className="empty" data-testid="transactions-empty-message">
                  Waiting for incoming transactions...
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;
