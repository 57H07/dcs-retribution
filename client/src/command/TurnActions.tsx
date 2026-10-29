// Turn actions at the bottom right of the command view (WEB-01.1): Begin
// Campaign / End turn, Take off with the Qt confirmations, sim speed controls
// and the player slot count, as QTopPanel's "Proceed" box had them.
import { commandErrorMessage } from "../api/commands";
import {
  SimSpeedJs,
  TopBar,
  useGetTopBarQuery,
  usePassTurnMutation,
  useSetSimSpeedMutation,
} from "../api/liberationApi";
import { Button, Modal, ModalClose, Tooltip, useToast } from "../ui";
import styles from "./TurnActions.module.css";
import { TakeOff, useTakeOff } from "./useTakeOff";

export const SIM_SPEEDS: { speed: SimSpeedJs; label: string }[] = [
  { speed: "paused", label: "Paused" },
  { speed: "1x", label: "1x" },
  { speed: "2x", label: "2x" },
  { speed: "5x", label: "5x" },
  { speed: "10x", label: "10x" },
  { speed: "100x", label: "100x" },
  { speed: "1000x", label: "1000x" },
];

function SimSpeedControls({ bar }: { bar: TopBar }) {
  const toast = useToast();
  const [setSimSpeed, { isLoading }] = useSetSimSpeedMutation();
  const change = async (speed: SimSpeedJs) => {
    const result = await setSimSpeed({ simSpeedChangeJs: { speed } });
    if ("error" in result) {
      toast({
        title: "Could not change the simulation speed",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    }
  };
  return (
    <div className={styles.speeds} role="group" aria-label="Simulation speed">
      {bar.sim.time != null && (
        <span className={styles.simTime} aria-label="Simulation time">
          {bar.sim.time}
        </span>
      )}
      {SIM_SPEEDS.map(({ speed, label }) => (
        <button
          key={speed}
          type="button"
          className={styles.speed}
          aria-pressed={bar.sim.speed === speed}
          disabled={isLoading || bar.turn === 0}
          onClick={() => change(speed)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function TakeOffDialogs({ takeOff }: { takeOff: TakeOff }) {
  const { step } = takeOff;
  const close = (open: boolean) => {
    if (!open) {
      takeOff.cancel();
    }
  };
  return (
    <>
      <Modal
        title="Continue without player pilots?"
        open={step.kind === "noPlayer"}
        onOpenChange={close}
        footer={
          <>
            <ModalClose asChild>
              <Button>No</Button>
            </ModalClose>
            <Button variant="primary" onClick={takeOff.continueWithoutPlayers}>
              Yes
            </Button>
          </>
        }
      >
        <p>
          No player pilots have been assigned to flights. Continuing will allow
          the AI to perform the mission, but players will be unable to
          participate.
        </p>
        <p>
          To assign player pilots to a flight, edit the flight of a package and
          assign specific pilots to it. If you have no player pilots available,
          the checkbox next to a pilot's name converts them to a player.
        </p>
        <p>
          Choose Yes to continue with an AI only mission, No to make more
          changes.
        </p>
      </Modal>
      <Modal
        title="Flights are missing pilots"
        open={step.kind === "missingPilots"}
        onOpenChange={close}
        footer={
          <ModalClose asChild>
            <Button variant="primary">Close</Button>
          </ModalClose>
        }
      >
        <p>The following flights are missing one or more pilots:</p>
        <ul>
          {(step.kind === "missingPilots" ? step.flights : []).map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
        <p>
          You must either assign pilots to those flights or cancel those
          missions.
        </p>
      </Modal>
      <Modal
        title="Continue with past start times?"
        open={step.kind === "pastStart"}
        onOpenChange={close}
        size="lg"
        footer={
          <>
            <ModalClose asChild>
              <Button>Cancel</Button>
            </ModalClose>
            <Button variant="danger" onClick={takeOff.launchAnyway}>
              Continue without fixing
            </Button>
            <Button variant="primary" onClick={takeOff.fixTotsAndLaunch}>
              Fix TOTs automatically
            </Button>
          </>
        }
      >
        <p>
          Some flights in the following packages have start times set earlier
          than mission start time:
        </p>
        <ul>
          {(step.kind === "pastStart" ? step.packages : []).map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
        <p>
          Flight start times are estimated based on the package TOT, so it is
          possible that not all flights will be able to reach the target area at
          their assigned times.
        </p>
        <p>
          You can either continue with the mission as planned, with the
          misplanned flights potentially flying too fast and/or missing their
          rendezvous; automatically fix negative TOTs; or cancel mission start
          and fix the packages manually.
        </p>
      </Modal>
    </>
  );
}

export function TurnActions() {
  const toast = useToast();
  // While the simulation runs, refresh its clock every second.
  const { data: bar } = useGetTopBarQuery();
  const running = bar != null && bar.sim.speed !== "paused";
  useGetTopBarQuery(undefined, {
    pollingInterval: running ? 1000 : 0,
    skip: !running,
  });
  const [passTurn, { isLoading: passingTurn }] = usePassTurnMutation();
  const takeOff = useTakeOff();
  const busy =
    takeOff.step.kind === "checking" || takeOff.step.kind === "launching";

  const onPassTurn = async () => {
    const result = await passTurn();
    if ("error" in result) {
      toast({
        title: "Could not pass the turn",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    }
  };

  const noGame = bar == null;
  const beginning = bar?.turn === 0;

  return (
    <div className={styles.actions}>
      {bar != null && bar.show_sim_speed_controls && (
        <SimSpeedControls bar={bar} />
      )}
      <div className={styles.buttons}>
        {bar != null && (
          <Tooltip
            content="Total number of client slots. To add client slots, edit a flight of a package."
            side="top"
          >
            <span className={styles.players} tabIndex={0}>
              Max players <strong>{bar.max_player_count}</strong>
            </span>
          </Tooltip>
        )}
        <Button
          size="lg"
          className={styles.turn}
          onClick={onPassTurn}
          disabled={noGame || passingTurn || busy}
        >
          {beginning ? "Begin Campaign" : "End turn"}
        </Button>
        <Button
          size="lg"
          variant="primary"
          className={styles.takeOff}
          onClick={takeOff.start}
          disabled={noGame || beginning || busy}
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            aria-hidden="true"
          >
            <path d="M2 16l20-8-6 12-3-5z" />
          </svg>
          {takeOff.step.kind === "launching" ? "Generating…" : "Take off"}
        </Button>
      </div>
      <TakeOffDialogs takeOff={takeOff} />
    </div>
  );
}
