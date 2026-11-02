// Production & repairs (issue #182), after mockups/Production.dc.html: everything
// in progress for the player and what waits for a decision. The engine lists the
// items and runs their actions (GET /production, POST /production/items/{id}/action):
// no game rule here.
import { commandErrorMessage } from "../api/commands";
import {
  Production,
  ProductionItem,
  useGetProductionQuery,
  useRunProductionActionMutation,
} from "../api/liberationApi";
import { formatMoney } from "../command/format";
import { QueryBody, ScreenFrame } from "../secondary/ScreenFrame";
import { PATHS } from "../shell/paths";
import { Button, useToast } from "../ui";
import styles from "./Production.module.css";
import { useNavigate } from "react-router-dom";

const GROUP_TITLES: Record<ProductionItem["group"], string> = {
  "aircraft-orders": "Aircraft on order",
  "ground-orders": "Ground units on order",
  maintenance: "Aircraft in maintenance",
  repairs: "Repairs",
  transfers: "Pending transfers",
  damage: "Damaged, waiting for money",
  ships: "Ships and carriers",
};

/** "1 turn", "3 turns". */
export function turnsText(turns: number): string {
  return turns === 1 ? "1 turn" : `${turns} turns`;
}

function actionText(action: NonNullable<ProductionItem["action"]>): string {
  if (action.cost > 0) {
    return `${action.label} · ${formatMoney(action.cost)}`;
  }
  return action.cost < 0
    ? `${action.label} · +${formatMoney(-action.cost)}`
    : action.label;
}

/** The screen that shows this item. */
function itemPath(item: ProductionItem): string | null {
  if (item.tgo_id) {
    return PATHS.tgo(item.tgo_id);
  }
  if (!item.base_id) {
    return null;
  }
  return item.group === "ground-orders"
    ? PATHS.baseTab(item.base_id, "ground-forces")
    : PATHS.base(item.base_id);
}

function Line({ item }: { item: ProductionItem }) {
  const navigate = useNavigate();
  const toast = useToast();
  const [run, { isLoading }] = useRunProductionActionMutation();
  const path = itemPath(item);
  const onAction = async () => {
    const result = await run({ itemId: item.id });
    if ("error" in result) {
      toast({
        title: `${item.action?.label ?? "Action"} refused`,
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    }
  };
  const action = item.action;
  return (
    <li className={styles.line}>
      <button
        type="button"
        className={styles.what}
        disabled={path === null}
        onClick={() => path && navigate(path)}
      >
        <span className={styles.label}>{item.label}</span>
        <span className={styles.detail}>{item.detail}</span>
      </button>
      <span className={styles.turns}>
        {item.turns != null ? turnsText(item.turns) : ""}
      </span>
      {action ? (
        <Button
          variant={action.cost > 0 ? "primary" : "secondary"}
          disabled={isLoading || !action.affordable}
          title={
            action.affordable ? undefined : "Not enough money for this action"
          }
          onClick={onAction}
        >
          {actionText(action)}
        </Button>
      ) : (
        <span className={styles.noAction}>Not cancellable</span>
      )}
    </li>
  );
}

function Panel(props: {
  title: string;
  items: ProductionItem[];
  empty: string;
}) {
  const groups = [...new Set(props.items.map((item) => item.group))];
  return (
    <section className={styles.panel} aria-label={props.title}>
      <h2 className={styles.title}>
        {props.title}
        <span className={styles.count}>{props.items.length}</span>
      </h2>
      {props.items.length === 0 && <p className={styles.empty}>{props.empty}</p>}
      {groups.map((group) => (
        <div key={group}>
          <h3 className={styles.group}>{GROUP_TITLES[group]}</h3>
          <ul className={styles.lines} aria-label={GROUP_TITLES[group]}>
            {props.items
              .filter((item) => item.group === group)
              .map((item) => (
                <Line key={item.id} item={item} />
              ))}
          </ul>
        </div>
      ))}
    </section>
  );
}

function Body({ production }: { production: Production }) {
  if (production.in_progress.length + production.to_handle.length === 0) {
    return <p className={styles.state}>Nothing in progress, nothing waiting.</p>;
  }
  return (
    <div className={styles.columns}>
      <Panel
        title="In progress"
        items={production.in_progress}
        empty="Nothing in progress."
      />
      <Panel
        title="To handle"
        items={production.to_handle}
        empty="Nothing waiting."
      />
    </div>
  );
}

export function ProductionScreen() {
  const query = useGetProductionQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  return (
    <ScreenFrame
      title="Production & repairs"
      actions={
        query.data && (
          <span className={styles.budget}>
            Budget <b>{formatMoney(query.data.budget)}</b>
          </span>
        )
      }
    >
      <QueryBody query={query} name="production">
        {(production) => <Body production={production} />}
      </QueryBody>
    </ScreenFrame>
  );
}
