// Campaign objectives (#194), from GET /objectives. The engine decides each
// state and caps each reward; the screen only shows them. Objectives never
// decide the end of the campaign: they only grant rewards.
import {
  CampaignObjective,
  CampaignObjectives,
  useGetObjectivesQuery,
} from "../api/liberationApi";
import objectiveStyles from "./ObjectivesScreen.module.css";
import { objectiveProgress } from "./objectiveProgress";
import { QueryBody, ScreenFrame } from "./ScreenFrame";
import styles from "./Secondary.module.css";

const TONES: Record<string, string | undefined> = {
  Met: "good",
  Missed: "bad",
};

function Objective({ objective }: { objective: CampaignObjective }) {
  const details = objectiveProgress(objective);
  return (
    <article className={objectiveStyles.objective} aria-label={objective.title}>
      <header className={objectiveStyles.header}>
        <h3 className={`${styles.cardTitle} ${objectiveStyles.title}`}>
          {objective.title}
        </h3>
        <span
          className={objectiveStyles.state}
          data-tone={TONES[objective.state]}
        >
          {objective.state}
          {objective.resolved_turn != null &&
            ` on turn ${objective.resolved_turn}`}
        </span>
      </header>
      {details && <span className={styles.cardDetail}>{details}</span>}
      {objective.state === "Met" ? (
        <span>
          {objective.granted
            ? `Reward granted: ${objective.granted}`
            : "No reward"}
        </span>
      ) : (
        objective.reward && (
          <>
            <span className={styles.cardDetail}>
              Reward: {objective.reward}
            </span>
            {objective.state === "In progress" &&
              objective.expected !== objective.reward && (
                // The settings scale and cap what the campaign promises.
                <span className={styles.cardDetail}>
                  With your settings today: {objective.expected || "no reward"}
                </span>
              )}
          </>
        )
      )}
    </article>
  );
}

function Objectives({ data }: { data: CampaignObjectives }) {
  if (data.objectives.length === 0) {
    return (
      <p className={styles.state}>
        This campaign has no objectives: its makers can set some in its YAML
        file.
      </p>
    );
  }
  return (
    <>
      <p className={styles.help}>
        Optional goals: a met objective grants its reward, a missed one costs
        nothing. The campaign is still won by taking every enemy base.
      </p>
      <div className={styles.list}>
        {data.objectives.map((objective, index) => (
          <Objective key={index} objective={objective} />
        ))}
      </div>
    </>
  );
}

export function ObjectivesScreen() {
  const query = useGetObjectivesQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  return (
    <ScreenFrame title="Objectives">
      <QueryBody query={query} name="objectives">
        {(data) => <Objectives data={data} />}
      </QueryBody>
    </ScreenFrame>
  );
}
