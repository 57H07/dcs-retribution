// Application log (WEB-08.2): the Qt logs window, read-only. GET /logs sends the
// last lines of the in-memory log; the screen polls it while open.
import { useGetLogsQuery } from "../api/liberationApi";
import { QueryBody, ScreenFrame } from "./ScreenFrame";
import styles from "./Secondary.module.css";
import { useEffect, useRef } from "react";

export const LOG_LINES = 1000;
export const LOG_POLL_MS = 2000;

export function LogsScreen() {
  const query = useGetLogsQuery(
    { lines: LOG_LINES },
    { pollingInterval: LOG_POLL_MS, refetchOnMountOrArgChange: true },
  );
  const console = useRef<HTMLPreElement>(null);
  const text = query.data?.lines.join("\n");
  // Follow the end of the log, as the Qt window did.
  useEffect(() => {
    const element = console.current;
    if (element) {
      element.scrollTop = element.scrollHeight;
    }
  }, [text]);

  const total = query.data?.total ?? 0;
  return (
    <ScreenFrame title="Logs">
      <QueryBody query={query} name="logs">
        {(log) =>
          !log.available ? (
            <p className={styles.state}>
              Logging keeps no log in memory (custom logging configuration): see
              the logs folder.
            </p>
          ) : (
            <>
              <p className={styles.help}>
                {total > log.lines.length
                  ? `Last ${log.lines.length} of ${total} lines. `
                  : ""}
                The full log is in logs/retribution.log.
              </p>
              <pre
                ref={console}
                className={styles.console}
                aria-label="Application log"
                tabIndex={0}
              >
                {text}
              </pre>
            </>
          )
        }
      </QueryBody>
    </ScreenFrame>
  );
}
