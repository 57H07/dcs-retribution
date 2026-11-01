// New campaign wizard (WEB-06), after mockups/NewGame.dc.html: Theater, Factions,
// Campaign options, Generator, Summary; then the generation with its progress, the
// air wing configuration, and turn 0. The engine owns the campaign list, the
// recommendations and every check.
import { commandErrorMessage } from "../api/commands";
import { AirWingConfigPanel } from "../airwingconfig/AirWingConfigPanel";
import {
  CampaignDefaults,
  NewGameCampaign,
  NewGameGeneration,
  NewGameOptions,
  useBeginNewGameMutation,
  useCancelNewGameGenerationMutation,
  useGetCampaignDefaultsQuery,
  useGetNewGameGenerationQuery,
  useGetNewGameOptionsQuery,
  useStartNewGameGenerationMutation,
} from "../api/liberationApi";
import { useCommand } from "../airwing/useCommand";
import { PATHS } from "../shell/paths";
import { Button } from "../ui";
import styles from "./NewGame.module.css";
import { FactionsStep } from "./FactionsStep";
import { GeneratorStep, OptionsStep } from "./OptionsSteps";
import { SummaryStep } from "./SummaryStep";
import { TheaterStep } from "./TheaterStep";
import { WizardState, stateFromDefaults, toRequest } from "./wizardState";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

const STEPS = [
  "Theater",
  "Factions",
  "Campaign options",
  "Generator",
  "Summary",
] as const;

function Header({ current }: { current: number }) {
  return (
    <header className={styles.header}>
      <h1 className={styles.title}>New campaign</h1>
      <ol className={styles.steps}>
        {STEPS.map((step, index) => (
          <li
            key={step}
            className={styles.step}
            aria-current={index === current ? "step" : undefined}
          >
            <span className={styles.stepIndex}>{index + 1}</span>
            <span className={styles.stepName}>{step}</span>
          </li>
        ))}
      </ol>
    </header>
  );
}

function Progress({ generation }: { generation: NewGameGeneration }) {
  const { step, step_index, step_count } = generation;
  const shown = step_count > 0 ? Math.min(step_index + 1, step_count) : 1;
  return (
    <div className={styles.progress} role="status">
      <h2 className={styles.heading}>
        {generation.status === "starting"
          ? "Starting the campaign"
          : "Generating the campaign"}
      </h2>
      <progress
        className={styles.bar}
        aria-label="Progress"
        max={Math.max(step_count, 1)}
        value={step == null ? 0 : step_index + 0.5}
      />
      <p className={styles.hint}>
        {step ?? "Starting…"}
        {step_count > 0 && ` · step ${shown} of ${step_count}`}
      </p>
    </div>
  );
}

function AirWingStep() {
  const [begin, beginState] = useBeginNewGameMutation();
  const [cancel] = useCancelNewGameGenerationMutation();
  const run = useCommand();
  return (
    <div className={styles.main}>
      <h2 className={styles.heading}>Air wing configuration</h2>
      <p className={styles.hint}>
        Customize the squadrons of both coalitions. You can change them later if
        the “Enable Air Wing adjustments” cheat is on.
      </p>
      <AirWingConfigPanel target="draft" />
      <div className={styles.footer}>
        <Button onClick={() => run(cancel(), "Could not discard the campaign")}>
          Discard campaign
        </Button>
        <span className={styles.spacer} />
        <Button
          variant="primary"
          size="lg"
          disabled={beginState.isLoading}
          onClick={() => run(begin(), "Could not start the campaign")}
        >
          Start campaign
        </Button>
      </div>
    </div>
  );
}

function Wizard({ options }: { options: NewGameOptions }) {
  const navigate = useNavigate();
  const [stepIndex, setStepIndex] = useState(0);
  const [campaign, setCampaign] = useState<NewGameCampaign | undefined>(
    () => options.campaigns.find((c) => c.compatible) ?? options.campaigns[0],
  );
  const [state, setState] = useState<WizardState>();
  const defaults = useGetCampaignDefaultsQuery(
    { campaignId: campaign?.id ?? "" },
    { skip: campaign === undefined },
  );
  const data: CampaignDefaults | undefined =
    defaults.currentData ?? undefined;
  const [start, startState] = useStartNewGameGenerationMutation();
  const run = useCommand();

  // A new campaign brings its recommendations: factions, date, budgets, settings.
  useEffect(() => {
    if (campaign !== undefined && data !== undefined) {
      setState(stateFromDefaults(campaign.id, data, options));
    }
  }, [campaign, data, options]);

  const ready =
    state !== undefined &&
    campaign !== undefined &&
    state.campaignId === campaign.id &&
    data !== undefined;
  const request = ready ? toRequest(state, options) : undefined;
  const last = stepIndex === STEPS.length - 1;

  let body = null;
  if (defaults.error && stepIndex > 0) {
    body = <p role="alert">{commandErrorMessage(defaults.error)}</p>;
  } else if (stepIndex > 0 && !ready) {
    body = <p className={styles.hint}>Loading the campaign…</p>;
  } else if (ready && stepIndex === 1) {
    body = <FactionsStep options={options} state={state} onChange={setState} />;
  } else if (ready && stepIndex === 2) {
    body = (
      <OptionsStep
        options={options}
        defaults={data}
        state={state}
        onChange={setState}
      />
    );
  } else if (ready && stepIndex === 3) {
    body = <GeneratorStep options={options} state={state} onChange={setState} />;
  } else if (ready && stepIndex === 4) {
    body = (
      <SummaryStep campaign={campaign} options={options} state={state} />
    );
  }

  const footer = (
    <div className={styles.footer}>
      <Button onClick={() => navigate(PATHS.command)}>Cancel</Button>
      <span className={styles.spacer} />
      <Button
        disabled={stepIndex === 0}
        onClick={() => setStepIndex(stepIndex - 1)}
      >
        Back
      </Button>
      {last ? (
        <Button
          variant="primary"
          size="lg"
          disabled={request === undefined || startState.isLoading}
          onClick={() =>
            request !== undefined &&
            run(
              start({ newGameRequestJs: request }),
              "The campaign was not generated",
            )
          }
        >
          Generate campaign
        </Button>
      ) : (
        <Button
          variant="primary"
          size="lg"
          disabled={campaign === undefined}
          onClick={() => setStepIndex(stepIndex + 1)}
        >
          Next · {STEPS[stepIndex + 1]}
        </Button>
      )}
    </div>
  );

  return (
    <>
      <Header current={stepIndex} />
      {stepIndex === 0 ? (
        <TheaterStep
          options={options}
          selected={campaign}
          onSelect={setCampaign}
          footer={footer}
        />
      ) : (
        <div className={styles.main}>
          {body}
          {footer}
        </div>
      )}
    </>
  );
}

export function NewGameScreen() {
  const navigate = useNavigate();
  const options = useGetNewGameOptionsQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  const [polling, setPolling] = useState(false);
  const generation = useGetNewGameGenerationQuery(undefined, {
    refetchOnMountOrArgChange: true,
    // The event stream tells each change; the poll covers a dropped event.
    pollingInterval: polling ? 1000 : 0,
  });
  const [cancel] = useCancelNewGameGenerationMutation();
  const status = generation.data?.status;

  useEffect(() => {
    setPolling(status === "generating" || status === "starting");
    if (status === "done") {
      // The shell installs the campaign; the wizard is ready for the next one.
      cancel();
      navigate(PATHS.command);
    }
  }, [status, cancel, navigate]);

  const busy = status === "generating" || status === "starting";
  const configuring = status === "configuring";
  return (
    <div className={styles.screen}>
      {busy && <Progress generation={generation.data!} />}
      {configuring && <AirWingStep />}
      {/* Stays mounted: a failure or a discarded draft comes back to the choices. */}
      <div className={styles.wizard} hidden={busy || configuring}>
        {status === "failed" && (
          <p role="alert" className={styles.warning}>
            {generation.data?.error}
          </p>
        )}
        {options.error ? (
          <p role="alert">{commandErrorMessage(options.error)}</p>
        ) : !options.data ? (
          <p className={styles.hint}>Loading the campaigns…</p>
        ) : (
          <Wizard options={options.data} />
        )}
      </div>
    </div>
  );
}
