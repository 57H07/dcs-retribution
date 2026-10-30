// Waiting for the mission result (WEB-05.1), after Qt's
// QWaitingForMissionResultWindow and in the visual language of
// mockups/Debrief.dc.html. The engine watches state.json and owns every rule
// (stale files, when results can be accepted): this screen shows the status of
// GET /game/mission/result, refetched on `mission_result_updated` events, and
// sends the commands. Accepting hands over to the Qt debriefing window until
// WEB-05.2.
import { commandErrorMessage } from "../api/commands";
import {
  LossRow,
  MissionResult,
  useAbortMissionMutation,
  useAcceptMissionResultMutation,
  useGetMissionResultQuery,
  useLoadMissionResultFileMutation,
} from "../api/liberationApi";
import { PATHS } from "../shell/paths";
import { Button, Table, TableColumn, useToast } from "../ui";
import styles from "./WaitingScreen.module.css";
import { Link, useNavigate } from "react-router-dom";

type Detection = {
  title: string;
  label: string;
  tone: "waiting" | "live" | "done" | "error";
};

/** What the screen says for each status of the engine. */
export function detection(result: MissionResult): Detection {
  switch (result.status) {
    case "waiting":
      return {
        title: "Waiting for mission result",
        label: "Waiting for state.json",
        tone: "waiting",
      };
    case "error":
      return {
        title: "Waiting for mission result",
        label: "Could not read state.json",
        tone: "error",
      };
    case "detected":
      return result.mission_ended
        ? { title: "Mission is over", label: "Mission over", tone: "done" }
        : {
            title: "Mission is being played",
            label: "Mission in progress",
            tone: "live",
          };
    default:
      return {
        title: "No mission in flight",
        label: "Not waiting",
        tone: "waiting",
      };
  }
}

function LossTable({ result }: { result: MissionResult }) {
  const columns: TableColumn<LossRow>[] = [
    { key: "label", header: "Losses", cell: (row) => row.label },
    {
      key: "blue",
      header: `${result.player_country ?? "Player"} (OwnFor)`,
      cell: (row) => row.blue,
      align: "end",
      mono: true,
    },
    {
      key: "red",
      header: `${result.enemy_country ?? "Enemy"} (OpFor)`,
      cell: (row) => row.red,
      align: "end",
      mono: true,
    },
  ];
  return (
    <Table
      caption="Mission status"
      columns={columns}
      rows={result.losses}
      rowKey={(row) => row.label}
    />
  );
}

export function WaitingScreen() {
  const { data: result } = useGetMissionResultQuery();
  const [loadFile, loading] = useLoadMissionResultFileMutation();
  const [abort, aborting] = useAbortMissionMutation();
  const [accept, accepting] = useAcceptMissionResultMutation();
  const navigate = useNavigate();
  const toast = useToast();
  const busy = loading.isLoading || aborting.isLoading || accepting.isLoading;

  const refused = (title: string, error: unknown) =>
    toast({
      title,
      description: commandErrorMessage(
        error as Parameters<typeof commandErrorMessage>[0],
      ),
      tone: "danger",
    });

  const onLoad = async () => {
    const answer = await loadFile();
    if ("error" in answer) {
      refused("state.json not loaded", answer.error);
    }
  };

  const onAbort = async () => {
    const answer = await abort();
    if ("error" in answer) {
      refused("Mission not aborted", answer.error);
      return;
    }
    toast({ title: "Mission aborted", description: "Back to planning." });
    navigate(PATHS.command);
  };

  const onAccept = async () => {
    const answer = await accept();
    if ("error" in answer) {
      refused("Results not accepted", answer.error);
      return;
    }
    toast({
      title: "Results accepted",
      description: `Turn ${answer.data.turn} begins.`,
      tone: "success",
    });
    navigate(PATHS.command);
  };

  if (result == null) {
    return (
      <section className={styles.screen} aria-label="Mission result">
        <p className={styles.empty}>Loading the mission status…</p>
      </section>
    );
  }

  const state = detection(result);
  const idle = result.status === "idle";

  return (
    <section className={styles.screen} aria-label="Mission result">
      <header className={styles.header}>
        <div className={styles.heading}>
          <span className={styles.eyebrow}>Mission in DCS</span>
          <h1 className={styles.title} data-tone={state.tone}>
            {state.title}
          </h1>
        </div>
        <div className={styles.spacer} />
        {idle ? (
          <Button asChild>
            <Link to={PATHS.command}>Back to the map</Link>
          </Button>
        ) : (
          <div className={styles.actions}>
            <Button onClick={onLoad} disabled={busy}>
              Load state.json
            </Button>
            <Button variant="danger" onClick={onAbort} disabled={busy}>
              Abort mission
            </Button>
            <Button
              variant="primary"
              size="lg"
              onClick={onAccept}
              disabled={busy || !result.mission_ended}
            >
              {accepting.isLoading ? "Processing results…" : "Accept results"}
            </Button>
          </div>
        )}
      </header>

      <div className={styles.body}>
        {idle ? (
          <p className={styles.empty}>
            No mission is waiting for its result. Take off from the command view
            to generate one.
          </p>
        ) : (
          <>
            <div className={styles.cards}>
              <div className={styles.card}>
                <span className={styles.cardLabel}>Mission file</span>
                <code className={styles.path}>{result.miz_path}</code>
                <span className={styles.hint}>
                  Start this mission in DCS. Its result is read from state.json
                  as it is played.
                </span>
              </div>
              <div className={styles.card}>
                <span className={styles.cardLabel}>Detection</span>
                <span
                  className={styles.status}
                  data-tone={state.tone}
                  role="status"
                >
                  <span className={styles.dot} aria-hidden />
                  {state.label}
                </span>
                {result.error != null && (
                  <span className={styles.error}>{result.error}</span>
                )}
                <code className={styles.path}>{result.state_path}</code>
                <span className={styles.hint}>
                  If DCS wrote it elsewhere, load it by hand: it is then taken
                  as the final result.
                </span>
              </div>
            </div>
            {result.losses.length > 0 && (
              <div className={styles.panel}>
                <LossTable result={result} />
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
