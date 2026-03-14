import { useEffect, useMemo, useRef, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import "./App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const POLLING_MS = 5000;

const API_SOURCES = [
  "http://localhost:8000/transactions",
  `${BACKEND_URL}/api/transactions`,
].filter(Boolean);

const getNumericValue = (value) => {
  if (value === null || value === undefined || value === "") {
    return 0;
  }

  const cleaned = typeof value === "string" ? value.replace(/,/g, "") : value;
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : 0;
};

const formatMoney = (value) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value || 0);

const formatTime = (value) => {
  if (!value) {
    return "--";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
};

const normalizeTransaction = (transaction, index) => {
  const time =
    transaction?.time ||
    transaction?.timestamp ||
    transaction?.created_at ||
    transaction?.createdAt ||
    "";

  const payer =
    transaction?.payer ||
    transaction?.customer ||
    transaction?.client_name ||
    transaction?.name ||
    "Unknown";

  const amount = getNumericValue(transaction?.amount ?? transaction?.total_amount);
  const gst = getNumericValue(transaction?.gst ?? transaction?.gst_amount);

  const computedNet = amount - gst;
  const net =
    transaction?.net !== undefined || transaction?.net_amount !== undefined
      ? getNumericValue(transaction?.net ?? transaction?.net_amount)
      : computedNet;

  const stableKey =
    transaction?.id ||
    transaction?._id ||
    transaction?.transaction_id ||
    `${time}-${payer}-${amount}-${gst}-${net}-${index}`;

  return {
    key: String(stableKey),
    rawTime: time,
    displayTime: formatTime(time),
    payer,
    amount,
    gst,
    net,
  };
};

const sortTransactionsNewestFirst = (items) =>
  [...items].sort((firstItem, secondItem) => {
    const firstDate = new Date(firstItem.rawTime).getTime();
    const secondDate = new Date(secondItem.rawTime).getTime();

    if (Number.isNaN(firstDate) && Number.isNaN(secondDate)) {
      return 0;
    }

    if (Number.isNaN(firstDate)) {
      return 1;
    }

    if (Number.isNaN(secondDate)) {
      return -1;
    }

    return secondDate - firstDate;
  });

function GstDashboard() {
  const [transactions, setTransactions] = useState([]);
  const [isOffline, setIsOffline] = useState(false);
  const [flashingRows, setFlashingRows] = useState(new Set());
  const previousKeysRef = useRef(new Set());
  const flashTimeoutRef = useRef(null);

  useEffect(() => {
    let isMounted = true;

    const pollTransactions = async () => {
      let fetchedTransactions = null;

      for (const endpoint of API_SOURCES) {
        try {
          const response = await fetch(endpoint, {
            method: "GET",
            headers: { Accept: "application/json" },
          });

          if (!response.ok) {
            throw new Error(`Failed with status ${response.status}`);
          }

          const payload = await response.json();
          const records = Array.isArray(payload)
            ? payload
            : Array.isArray(payload?.transactions)
              ? payload.transactions
              : [];

          fetchedTransactions = sortTransactionsNewestFirst(
            records.map((item, index) => normalizeTransaction(item, index))
          );
          break;
        } catch (_error) {
          fetchedTransactions = null;
        }
      }

      if (!isMounted) {
        return;
      }

      if (fetchedTransactions === null) {
        setIsOffline(true);
        return;
      }

      const incomingKeys = new Set(fetchedTransactions.map((transaction) => transaction.key));
      const newRows = fetchedTransactions
        .filter((transaction) => !previousKeysRef.current.has(transaction.key))
        .map((transaction) => transaction.key);

      if (flashTimeoutRef.current) {
        clearTimeout(flashTimeoutRef.current);
      }

      setFlashingRows(new Set(newRows));
      flashTimeoutRef.current = setTimeout(() => {
        if (isMounted) {
          setFlashingRows(new Set());
        }
      }, 1200);

      previousKeysRef.current = incomingKeys;
      setTransactions(fetchedTransactions);
      setIsOffline(false);
    };

    pollTransactions();
    const intervalId = setInterval(pollTransactions, POLLING_MS);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
      if (flashTimeoutRef.current) {
        clearTimeout(flashTimeoutRef.current);
      }
    };
  }, []);

  const totals = useMemo(
    () =>
      transactions.reduce(
        (acc, transaction) => {
          acc.gst += transaction.gst;
          acc.collected += transaction.amount;
          acc.net += transaction.net;
          return acc;
        },
        { gst: 0, collected: 0, net: 0 }
      ),
    [transactions]
  );

  return (
    <main className="gst-dashboard min-h-screen px-4 py-8 md:px-8" data-testid="gst-dashboard">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="relative flex flex-wrap items-start justify-between gap-3" data-testid="dashboard-header">
          <div>
            <h1
              className="text-4xl font-semibold tracking-tight text-white sm:text-5xl"
              data-testid="dashboard-title"
            >
              Real-time GST Billing Tracker
            </h1>
            <div className="mt-3 flex items-center gap-2 text-sm text-[#9ca3af]" data-testid="live-status-indicator">
              <span className="live-dot" data-testid="live-status-dot" />
              <span data-testid="live-status-label">Live</span>
            </div>
          </div>

          {isOffline && (
            <Badge
              className="offline-badge absolute right-0 top-0 border-[#374151] bg-[#1f2937] text-[#e5e7eb]"
              data-testid="offline-badge"
              variant="outline"
            >
              Offline
            </Badge>
          )}
        </header>

        <section className="grid grid-cols-1 gap-4 lg:grid-cols-4" data-testid="summary-cards-section">
          <Card
            className="card-surface border-[#2a2a2a] lg:col-span-2"
            data-testid="march-gst-total-card"
          >
            <CardHeader className="pb-3">
              <CardTitle className="text-base text-[#9ca3af]" data-testid="march-gst-total-label">
                March GST Total
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p
                className="number-mono text-4xl font-semibold text-[#22c55e] sm:text-5xl"
                data-testid="march-gst-total-value"
              >
                {formatMoney(totals.gst)}
              </p>
            </CardContent>
          </Card>

          <Card className="card-surface border-[#2a2a2a]" data-testid="total-collected-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-[#9ca3af]" data-testid="total-collected-label">
                Total Collected
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="number-mono text-2xl font-medium text-white" data-testid="total-collected-value">
                {formatMoney(totals.collected)}
              </p>
            </CardContent>
          </Card>

          <Card className="card-surface border-[#2a2a2a]" data-testid="net-total-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-[#9ca3af]" data-testid="net-total-label">
                Net (excl. GST)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="number-mono text-2xl font-medium text-white" data-testid="net-total-value">
                {formatMoney(totals.net)}
              </p>
            </CardContent>
          </Card>
        </section>

        <section className="w-full" data-testid="transactions-section">
          <Card className="card-surface border-[#2a2a2a]" data-testid="transactions-table-card">
            <CardHeader>
              <CardTitle className="text-base text-white" data-testid="transactions-table-title">
                Transactions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table className="w-full" data-testid="transactions-table">
                <TableHeader data-testid="transactions-table-header">
                  <TableRow className="border-[#27272a] hover:bg-transparent" data-testid="transactions-header-row">
                    <TableHead className="text-[#9ca3af]" data-testid="transactions-head-time">
                      Time
                    </TableHead>
                    <TableHead className="text-[#9ca3af]" data-testid="transactions-head-payer">
                      Payer
                    </TableHead>
                    <TableHead className="text-right text-[#9ca3af]" data-testid="transactions-head-amount">
                      Amount
                    </TableHead>
                    <TableHead className="text-right text-[#9ca3af]" data-testid="transactions-head-gst">
                      GST
                    </TableHead>
                    <TableHead className="text-right text-[#9ca3af]" data-testid="transactions-head-net">
                      Net
                    </TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody data-testid="transactions-table-body">
                  {transactions.length === 0 ? (
                    <TableRow className="border-[#232323]" data-testid="transactions-empty-row">
                      <TableCell
                        className="py-8 text-center text-sm text-[#9ca3af]"
                        colSpan={5}
                        data-testid="transactions-empty-state"
                      >
                        Waiting for transactions…
                      </TableCell>
                    </TableRow>
                  ) : (
                    transactions.map((transaction, index) => (
                      <TableRow
                        className={`border-[#232323] ${index % 2 === 0 ? "row-even" : "row-odd"} ${
                          flashingRows.has(transaction.key) ? "row-flash" : ""
                        }`}
                        data-testid={`transaction-row-${transaction.key}`}
                        key={transaction.key}
                      >
                        <TableCell className="text-[#f9fafb]" data-testid={`transaction-time-${index}`}>
                          {transaction.displayTime}
                        </TableCell>
                        <TableCell className="text-[#f9fafb]" data-testid={`transaction-payer-${index}`}>
                          {transaction.payer}
                        </TableCell>
                        <TableCell
                          className="number-mono text-right text-[#f9fafb]"
                          data-testid={`transaction-amount-${index}`}
                        >
                          {formatMoney(transaction.amount)}
                        </TableCell>
                        <TableCell
                          className="number-mono text-right text-[#22c55e]"
                          data-testid={`transaction-gst-${index}`}
                        >
                          {formatMoney(transaction.gst)}
                        </TableCell>
                        <TableCell
                          className="number-mono text-right text-[#f9fafb]"
                          data-testid={`transaction-net-${index}`}
                        >
                          {formatMoney(transaction.net)}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<GstDashboard />} path="/" />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
