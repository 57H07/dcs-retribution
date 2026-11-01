// Base screen (WEB-02.1), after mockups/Base.dc.html: the Qt base menu with its
// status (runway, parking, depots, air defense) and repairs on the side, and
// its tabs. The engine decides everything (GET /control-points/{id}/base): which
// tabs a base has, what can be repaired, at what cost, and whether it is
// affordable; refusals come back as toasts.
import { commandErrorMessage } from "../api/commands";
import {
  AirDefense,
  Base,
  IntelGroup,
  Repair,
  useGetBaseQuery,
  useOrderAllRepairsMutation,
  useOrderRepairMutation,
} from "../api/liberationApi";
import {
  ControlPointGauges,
  distanceText,
} from "../command/inspector/MapInspector";
import { BaseTabId, PATHS } from "../shell/paths";
import { useQtCommands } from "../shell/useQtCommands";
import settings from "../settings/SettingsScreen.module.css";
import {
  Button,
  MilSymbol,
  Table,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  useToast,
} from "../ui";
import styles from "./BaseScreen.module.css";
import { ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

/** "$100M", "$2.5M": the money figures of the Qt base menu. */
export function money(millions: number): string {
  return `$${Number(millions.toFixed(1))}M`;
}

function turns(count: number): string {
  return count === 1 ? "1 turn" : `${count} turns`;
}

/** "$25M · 3 turns", or what is left of a repair underway. */
export function repairTerms(repair: Repair): string {
  if (repair.in_progress) {
    const what = repair.kind === "aircraft" ? "In maintenance" : "Repairing";
    return `${what} · ${turns(repair.turns)} left`;
  }
  return `${money(repair.cost)} · ${repair.turns === 0 ? "at once" : turns(repair.turns)}`;
}

export function BaseScreen() {
  const { id = "", tab } = useParams();
  const { data, error, isLoading } = useGetBaseQuery({ cpId: id });

  return (
    <div className={settings.screen}>
      <header className={settings.header}>
        <Link to={PATHS.command} className={settings.back}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path d="M15 6l-6 6 6 6" />
          </svg>
          Command view
        </Link>
        <span className={settings.divider} />
        {data ? (
          <BaseTitle base={data} />
        ) : (
          <h1 className={settings.title}>Base</h1>
        )}
      </header>
      {isLoading ? (
        <p className={styles.state}>Loading the base…</p>
      ) : error ? (
        <p className={styles.state} role="alert">
          {commandErrorMessage(error) ?? "This base is not available."}
        </p>
      ) : data == null ? (
        <p className={styles.state}>No campaign loaded.</p>
      ) : (
        <BaseBody base={data} tab={tab} />
      )}
    </div>
  );
}

function BaseTitle({ base }: { base: Base }) {
  const { summary } = base;
  const subtitle = [
    summary.category,
    distanceText(summary.distance_to_front_nm),
  ]
    .filter((part) => part !== null)
    .join(" · ");
  return (
    <>
      <MilSymbol
        sidc={summary.sidc}
        size={26}
        label={`${summary.blue ? "Friendly" : "Enemy"} ${summary.category}`}
      />
      <h1 className={settings.title}>{summary.name}</h1>
      <span className={styles.subtitle}>{subtitle}</span>
      <span className={styles.spacer} />
      <div className={styles.budget}>
        <span className={styles.budgetLabel}>Budget</span>
        <span className={styles.mono}>{money(base.budget)}</span>
      </div>
    </>
  );
}

function BaseBody({ base, tab }: { base: Base; tab: string | undefined }) {
  const navigate = useNavigate();
  const cpId = base.summary.id;
  // An unknown tab (or none) shows the first tab this base has.
  const current =
    base.tabs.find((t) => t.id === tab)?.id ?? base.tabs[0]?.id ?? "intel";

  return (
    <div className={styles.body}>
      <aside className={styles.side}>
        <StatusPanel base={base} />
        {base.summary.blue && <RepairsPanel base={base} />}
        <AirDefensePanel defenses={base.air_defenses} />
      </aside>
      <Tabs
        className={styles.tabs}
        value={current}
        onValueChange={(value) =>
          navigate(PATHS.baseTab(cpId, value as BaseTabId), { replace: true })
        }
      >
        <TabsList aria-label="Base sections" className={styles.tabList}>
          {base.tabs.map((t) => (
            <TabsTrigger key={t.id} value={t.id}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {base.tabs.map((t) => (
          <TabsContent key={t.id} value={t.id} className={styles.content}>
            <TabBody tab={t.id} base={base} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

const PLACEHOLDERS: Record<
  Exclude<BaseTabId, "intel">,
  { title: string; text: string }
> = {
  airfield: {
    title: "Squadrons",
    text: "Aircraft purchases and new squadrons are not in the web interface yet.",
  },
  "ground-forces": {
    title: "Ground forces",
    text: "Ground unit purchases and transfers are not in the web interface yet.",
  },
  convoys: {
    title: "Departing convoys",
    text: "Departing convoys are not in the web interface yet.",
  },
};

function TabBody({ tab, base }: { tab: BaseTabId; base: Base }) {
  if (tab === "intel") {
    return <IntelTab groups={base.intel} />;
  }
  return <Placeholder cpId={base.summary.id} {...PLACEHOLDERS[tab]} />;
}

/** Until WEB-02.2 and WEB-02.3: the Qt base menu does the rest. */
function Placeholder(props: { cpId: string; title: string; text: string }) {
  const qt = useQtCommands();
  return (
    <section className={styles.placeholder} aria-label={props.title}>
      <h2 className={styles.panelTitle}>{props.title}</h2>
      <p>{props.text}</p>
      <Button onClick={() => qt.openBase(props.cpId)}>
        Open the base menu
      </Button>
    </section>
  );
}

function Panel(props: { title: string; children: ReactNode }) {
  return (
    <section className={styles.panel} aria-label={props.title}>
      <h2 className={styles.panelTitle}>{props.title}</h2>
      {props.children}
    </section>
  );
}

function StatusPanel({ base }: { base: Base }) {
  return (
    <Panel title="Base status">
      <ControlPointGauges summary={base.summary} />
    </Panel>
  );
}

function AirDefensePanel({ defenses }: { defenses: AirDefense[] }) {
  return (
    <Panel title="Air defense">
      {defenses.length === 0 ? (
        <p className={styles.warning}>No air defense site at this base.</p>
      ) : (
        <ul className={styles.list}>
          {defenses.map((site) => (
            <li key={site.id} className={styles.row}>
              <span>
                {site.name}
                <span className={styles.muted}> · {site.category}</span>
              </span>
              <span
                className={site.operational ? styles.mono : styles.warningMono}
              >
                {site.units.current}/{site.units.total}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

type Result = { error?: unknown } | { data: unknown };

function RepairsPanel({ base }: { base: Base }) {
  const toast = useToast();
  const [orderRepair, repairState] = useOrderRepairMutation();
  const [orderAll, allState] = useOrderAllRepairsMutation();
  const busy = repairState.isLoading || allState.isLoading;
  const cpId = base.summary.id;
  const orderable = base.repairs.filter((r) => !r.in_progress);

  const report = async (pending: Promise<Result>, done: string) => {
    const result = await pending;
    if ("error" in result && result.error !== undefined) {
      toast({
        title: "Repair refused",
        description: commandErrorMessage(
          result.error as Parameters<typeof commandErrorMessage>[0],
        ),
        tone: "danger",
      });
    } else {
      toast({ title: done, tone: "success" });
    }
  };

  return (
    <Panel title="Repairs">
      {base.repairs.length === 0 ? (
        <p className={styles.muted}>Nothing to repair.</p>
      ) : (
        <ul className={styles.list}>
          {base.repairs.map((repair) => (
            <li key={repair.id} className={styles.repair}>
              <div className={styles.repairText}>
                <span>{repair.label}</span>
                <span className={styles.muted}>{repairTerms(repair)}</span>
              </div>
              {!repair.in_progress && (
                <Button
                  disabled={busy || !repair.affordable}
                  title={
                    repair.affordable
                      ? undefined
                      : "Not enough money for the repair"
                  }
                  aria-label={`Repair ${repair.label}`}
                  onClick={() =>
                    report(
                      orderRepair({ cpId, repairId: repair.id }),
                      `Repair ordered: ${repair.label}`,
                    )
                  }
                >
                  Repair
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      {orderable.length > 1 && (
        <Button
          disabled={busy || !base.repair_all_affordable}
          title={
            base.repair_all_affordable
              ? undefined
              : "Not enough money for every repair"
          }
          onClick={() => report(orderAll({ cpId }), "Every repair ordered")}
        >
          Repair all · {money(base.repair_all_cost)}
        </Button>
      )}
    </Panel>
  );
}

function IntelTab({ groups }: { groups: IntelGroup[] }) {
  return (
    <div className={styles.intel}>
      {groups.map((group) => (
        <Table
          key={group.title}
          caption={group.title}
          columns={[
            { key: "name", header: "Unit", cell: (u) => u.name },
            {
              key: "count",
              header: "Count",
              cell: (u) => u.count,
              align: "end",
              mono: true,
            },
          ]}
          rows={group.units}
          rowKey={(u) => u.name}
          emptyText="None"
        />
      ))}
    </div>
  );
}
