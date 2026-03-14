import { AppendInput, AppendRecord, S2 } from "@s2-dev/streamstore";

const authToken = process.env.REACT_APP_S2_AUTH_TOKEN;
const basinName = process.env.REACT_APP_S2_BASIN || "gst-transactions";
const STREAM = "transactions";

let streamClient = null;

const getStreamClient = async () => {
  if (!authToken) {
    throw new Error("S2 token missing");
  }

  if (streamClient) {
    return streamClient;
  }

  const s2 = new S2({ accessToken: authToken });
  const basin = s2.basin(basinName);

  try {
    await basin.streams.create({ stream: STREAM });
  } catch (error) {
    const message = String(error?.message || "").toLowerCase();
    if (!message.includes("already exists")) {
      throw error;
    }
  }

  streamClient = basin.stream(STREAM);
  return streamClient;
};

export const initStream = async () => {
  await getStreamClient();
};

export const pushTransaction = async (tx) => {
  const stream = await getStreamClient();
  await stream.append(
    AppendInput.create([
      AppendRecord.string({
        body: JSON.stringify({ ...tx, timestamp: new Date().toISOString() }),
      }),
    ]),
  );
};

export const subscribeTransactions = async (onTx, onError) => {
  const stream = await getStreamClient();
  const session = await stream.readSession({
    start: { from: { tailOffset: 0 }, clamp: true },
  });

  let cancelled = false;

  (async () => {
    try {
      for await (const record of session) {
        if (cancelled) {
          break;
        }

        if (!record?.body) {
          continue;
        }

        try {
          onTx(JSON.parse(record.body));
        } catch (_err) {
          // Skip malformed events
        }
      }
    } catch (error) {
      if (!cancelled) {
        onError?.(error);
      }
    }
  })();

  return async () => {
    cancelled = true;
    try {
      await session.cancel();
    } catch (_err) {
      // Session may already be closed
    }
  };
};
