// Ground object sheet (WEB-08.3), the web version of the Qt QGroundObjectMenu: units
// or buildings with their status and repairs, orientation, MFD hiding, disbanding,
// and replacing the group (BuyDialog). The engine decides everything through
// GET /tgos/{id}/sheet; refusals come back as toasts.
import { commandErrorMessage } from "../api/commands";
import {
  TgoSheet,
  TgoUnit,
  useDisbandTgoGroupMutation,
  useGetTgoSheetQuery,
  useRepairTgoUnitMutation,
  useSetTgoHeadingMutation,
  useSetTgoHiddenOnMfdMutation,
} from "../api/liberationApi";
import { money } from "../bases/money";
import { distanceText, TgoGauges } from "../command/inspector/MapInspector";
import { QueryBody, ScreenFrame } from "../secondary/ScreenFrame";
import secondary from "../secondary/Secondary.module.css";
import { PATHS } from "../shell/paths";
import {
  Button,
  MilSymbol,
  Modal,
  ModalClose,
  NumberField,
  Switch,
  useToast,
} from "../ui";
import { BuyDialog } from "./BuyDialog";
import styles from "./TgoScreen.module.css";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

type Result = { error?: unknown } | { data: unknown };

function turns(count: number): string {
  return count === 1 ? "1 turn" : `${count} turns`;
}

/** "Repairing · 2 turns left", "Destroyed"... */
export function unitStateText(unit: TgoUnit): string {
  switch (unit.state) {
    case "operational":
      return "Operational";
    case "destroyed":
      return "Destroyed";
    case "repairing":
      return `Repairing · ${turns(unit.turns_remaining)} left`;
    case "inoperative":
      return `Inoperative · ${turns(unit.turns_remaining)} left`;
  }
}

/** "Repair · $25M", with the delay when there is one. */
export function repairText(unit: TgoUnit): string {
  const delay = unit.repair_turns ? ` · ${turns(unit.repair_turns)}` : "";
  return `Repair · ${money(unit.repair_cost ?? 0)}${delay}`;
}

/** Runs a command of this screen; a refusal becomes a toast. */
function useReport() {
  const toast = useToast();
  return async (pending: Promise<Result>, title: string, done?: string) => {
    const result = await pending;
    if ("error" in result && result.error !== undefined) {
      toast({
        title,
        description: commandErrorMessage(
          result.error as Parameters<typeof commandErrorMessage>[0],
        ),
        tone: "danger",
      });
    } else if (done) {
      toast({ title: done, tone: "success" });
    }
  };
}

export function TgoScreen() {
  const { id = "" } = useParams();
  const query = useGetTgoSheetQuery({ tgoId: id });
  const sheet = query.data;
  return (
    <ScreenFrame
      title={sheet?.summary.name ?? "Site"}
      actions={
        sheet && (
          <>
            {sheet.summary.blue && (
              <span className={styles.budget}>
                Budget{" "}
                <span className={secondary.mono}>{money(sheet.budget)}</span>
              </span>
            )}
            <Button asChild>
              <Link to={PATHS.base(sheet.summary.control_point_id)}>
                {sheet.summary.control_point_name}
              </Link>
            </Button>
          </>
        )
      }
    >
      <QueryBody query={query} name="site details">
        {(data) => <SheetBody tgoId={id} sheet={data} />}
      </QueryBody>
    </ScreenFrame>
  );
}

function SheetBody({ tgoId, sheet }: { tgoId: string; sheet: TgoSheet }) {
  const { summary } = sheet;
  const subtitle = [
    summary.category,
    summary.control_point_name,
    distanceText(summary.distance_to_front_nm),
  ]
    .filter((part) => part !== null)
    .join(" · ");
  return (
    <>
      <section className={styles.status} aria-label="Status">
        <MilSymbol
          sidc={summary.sidc}
          size={32}
          label={`${summary.blue ? "Friendly" : "Enemy"} ${summary.category}`}
        />
        <div className={styles.statusText}>
          <span className={secondary.cardDetail}>{subtitle}</span>
          <TgoGauges summary={summary} />
        </div>
      </section>
      {sheet.income && (
        <section className={secondary.section} aria-label="Finances">
          <h2 className={secondary.sectionTitle}>Finances</h2>
          <p className={secondary.prose}>
            Receiving {money(sheet.income.receiving)} of{" "}
            {money(sheet.income.available)} per turn (
            {money(sheet.income.per_building)} per building).
          </p>
        </section>
      )}
      <UnitsSection tgoId={tgoId} sheet={sheet} />
      {sheet.heading && <OrientationSection tgoId={tgoId} sheet={sheet} />}
      {sheet.hidden_on_mfd != null && (
        <HiddenSection tgoId={tgoId} hidden={sheet.hidden_on_mfd} />
      )}
      {sheet.can_buy && <ForcesSection tgoId={tgoId} sheet={sheet} />}
    </>
  );
}

function UnitsSection({ tgoId, sheet }: { tgoId: string; sheet: TgoSheet }) {
  const [repair, { isLoading }] = useRepairTgoUnitMutation();
  const report = useReport();
  const title = sheet.is_building_site ? "Buildings" : "Units";
  return (
    <section className={secondary.section} aria-label={title}>
      <h2 className={secondary.sectionTitle}>
        {title} <span className={secondary.count}>{sheet.units.length}</span>
      </h2>
      {sheet.units.length === 0 && (
        <p className={secondary.help}>Nothing left at this site.</p>
      )}
      <ul className={styles.units}>
        {sheet.units.map((unit) => (
          <li key={unit.id} className={styles.unit}>
            <UnitName unit={unit} />
            <span
              className={
                unit.state === "operational" ? secondary.help : styles.damaged
              }
            >
              {unitStateText(unit)}
            </span>
            {unit.repair_cost != null && (
              <Button
                disabled={isLoading || !unit.repair_affordable}
                title={
                  unit.repair_affordable
                    ? undefined
                    : "Not enough money for the repair"
                }
                aria-label={`Repair ${unit.name} (${unit.id})`}
                onClick={() =>
                  report(
                    repair({ tgoId, unitId: unit.id }),
                    "Repair refused",
                    `Repair ordered: ${unit.name}`,
                  )
                }
              >
                {repairText(unit)}
              </Button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

function UnitName({ unit }: { unit: TgoUnit }) {
  if (unit.info_kind != null && unit.info_name != null) {
    return (
      <Link
        className={styles.unitName}
        to={PATHS.unit(unit.info_kind, unit.info_name)}
      >
        {unit.name}
      </Link>
    );
  }
  return <span className={styles.unitName}>{unit.name}</span>;
}

function OrientationSection({
  tgoId,
  sheet,
}: {
  tgoId: string;
  sheet: TgoSheet;
}) {
  const [setHeading, { isLoading }] = useSetTgoHeadingMutation();
  const report = useReport();
  const heading = sheet.heading;
  if (!heading) {
    return null;
  }
  const turn = (degrees: number) =>
    report(
      setHeading({ tgoId, tgoHeadingChangeJs: { degrees } }),
      "Could not turn the site",
    );
  return (
    <section className={secondary.section} aria-label="Orientation">
      <h2 className={secondary.sectionTitle}>Orientation</h2>
      <div className={styles.controls}>
        <NumberField
          label="Heading"
          unit="°"
          min={0}
          max={359}
          step={5}
          value={heading.degrees}
          disabled={!heading.can_adjust || isLoading}
          onValueChange={turn}
        />
        {heading.can_adjust && (
          <Button
            disabled={isLoading || heading.degrees === heading.to_conflict}
            onClick={() => turn(heading.to_conflict)}
          >
            Head to conflict
          </Button>
        )}
      </div>
    </section>
  );
}

function HiddenSection({ tgoId, hidden }: { tgoId: string; hidden: boolean }) {
  const [setHidden, { isLoading }] = useSetTgoHiddenOnMfdMutation();
  const report = useReport();
  return (
    <section className={secondary.section} aria-label="MFD">
      <Switch
        label="Hidden on MFD"
        checked={hidden}
        disabled={isLoading}
        onCheckedChange={(checked) =>
          report(
            setHidden({ tgoId, tgoHiddenChangeJs: { hidden: checked } }),
            "Could not change this site",
          )
        }
      />
    </section>
  );
}

function ForcesSection({ tgoId, sheet }: { tgoId: string; sheet: TgoSheet }) {
  const [buying, setBuying] = useState(false);
  const [disbanding, setDisbanding] = useState(false);
  const [disband, { isLoading }] = useDisbandTgoGroupMutation();
  const report = useReport();
  return (
    <section className={secondary.section} aria-label="Forces">
      <h2 className={secondary.sectionTitle}>Forces</h2>
      <div className={styles.controls}>
        <Button variant="primary" onClick={() => setBuying(true)}>
          Buy / Replace
        </Button>
        {sheet.disband_value > 0 && (
          <Button variant="danger" onClick={() => setDisbanding(true)}>
            Disband · +{money(sheet.disband_value)}
          </Button>
        )}
      </div>
      {buying && (
        <BuyDialog
          tgoId={tgoId}
          siteName={sheet.summary.name}
          onClose={() => setBuying(false)}
        />
      )}
      <Modal
        title={`Disband ${sheet.summary.name}?`}
        open={disbanding}
        onOpenChange={setDisbanding}
        footer={
          <>
            <ModalClose asChild>
              <Button>Cancel</Button>
            </ModalClose>
            <Button
              variant="danger"
              disabled={isLoading}
              onClick={async () => {
                await report(
                  disband({ tgoId }),
                  "Disband refused",
                  `${sheet.summary.name} disbanded`,
                );
                setDisbanding(false);
              }}
            >
              Disband
            </Button>
          </>
        }
      >
        All the units leave this site and {money(sheet.disband_value)} return to
        the budget.
      </Modal>
    </section>
  );
}
