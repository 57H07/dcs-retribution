// "Radios & TACAN" tab of a flight (WEB-04.5): the frequency of the flight and of its
// package, a tanker's TACAN, the datalink of each member, and what belongs to the
// departure base (ICLS, Link 4), edited with the panel of the base screen. Changes
// apply at once, each command answers the whole tab; the server enforces the limits and
// says what is worth a warning. The data cartridge of the last mission (#191) is saved
// from here, through the native save dialog.
import { commandErrorMessage } from "../api/commands";
import {
  DatalinkField,
  DatalinkMember,
  FlightDatalink,
  FlightRadios,
  RadioRange,
  useGetBaseActionsQuery,
  useGetFlightRadiosQuery,
  useSaveFlightCartridgeMutation,
  useSetFlightDatalinkMutation,
  useSetFlightFrequencyMutation,
  useSetFlightTacanMutation,
  useSetPackageFrequencyMutation,
} from "../api/liberationApi";
import { RadiosPanel } from "../bases/BaseActionsPanels";
import { Button, useToast } from "../ui";
import styles from "./FlightRadiosTab.module.css";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

type Result = { error?: unknown } | { data: unknown };

/** Shows a refused command as a toast; true when it went through. */
function useCommandReport() {
  const toast = useToast();
  return (title: string, result: Result): boolean => {
    if ("error" in result && result.error !== undefined) {
      toast({
        title,
        description: commandErrorMessage(
          result.error as Parameters<typeof commandErrorMessage>[0],
        ),
        tone: "danger",
      });
      return false;
    }
    return true;
  };
}

function text(value: number | string | null | undefined): string {
  return value != null ? `${value}` : "";
}

export function FlightRadiosTab({ flightId }: { flightId: string }) {
  // The route of the package editor (see PackageEditor).
  const { id: packageId = "" } = useParams();
  const { data, error, isLoading } = useGetFlightRadiosQuery({
    packageId,
    flightId,
  });
  if (isLoading) {
    return <p className={styles.hint}>Loading the radios…</p>;
  }
  if (error || data == null) {
    return (
      <p className={styles.hint} role="alert">
        {commandErrorMessage(
          error as Parameters<typeof commandErrorMessage>[0],
        ) ?? "The radios of this flight are not available."}
      </p>
    );
  }
  return (
    <div className={styles.tab}>
      <FlightFrequency
        packageId={packageId}
        flightId={flightId}
        radios={data}
      />
      <PackageFrequency
        packageId={packageId}
        flightId={flightId}
        radios={data}
      />
      {data.has_tacan && (
        <FlightTacan packageId={packageId} flightId={flightId} radios={data} />
      )}
      {data.datalink != null && (
        <Datalink
          packageId={packageId}
          flightId={flightId}
          datalink={data.datalink}
        />
      )}
      <DepartureRadios cpId={data.departure_id} name={data.departure} />
      <DataCartridge packageId={packageId} flightId={flightId} radios={data} />
    </div>
  );
}

type FlightProps = {
  packageId: string;
  flightId: string;
  radios: FlightRadios;
};

function Warnings({ warnings }: { warnings: string[] }) {
  return (
    <>
      {warnings.map((warning) => (
        <p key={warning} className={styles.warning} role="status">
          {warning}
        </p>
      ))}
    </>
  );
}

function rangeLabel(range: RadioRange): string {
  return `${range.min_mhz}–${range.max_mhz} MHz ${range.modulation}`;
}

/** The modulations the radio has at this frequency, or all it has. */
function modulationsAt(ranges: RadioRange[], mhz: number): string[] {
  const covering = ranges.filter((r) => r.min_mhz <= mhz && mhz < r.max_mhz);
  return [
    ...new Set(
      (covering.length > 0 ? covering : ranges).map((r) => r.modulation),
    ),
  ].sort();
}

function FlightFrequency({ packageId, flightId, radios }: FlightProps) {
  const report = useCommandReport();
  const [setFrequency, { isLoading }] = useSetFlightFrequencyMutation();
  const current = text(radios.frequency_mhz);
  const [draft, setDraft] = useState(current);
  const [modulation, setModulation] = useState(radios.modulation ?? "");
  useEffect(() => setDraft(current), [current]);
  useEffect(() => setModulation(radios.modulation ?? ""), [radios.modulation]);

  const offered = modulationsAt(radios.ranges, Number(draft));
  const chosen = offered.includes(modulation) ? modulation : offered[0];
  const send = (mhz: number | null, sentModulation: string | null) =>
    setFrequency({
      packageId,
      flightId,
      flightFrequencyJs: { mhz, modulation: sentModulation },
    });

  return (
    <section className={styles.panel} aria-label="Flight frequency">
      <h3 className={styles.title}>Flight frequency</h3>
      <div className={styles.fields}>
        <label className={styles.field}>
          MHz
          <input
            className={styles.input}
            inputMode="decimal"
            placeholder="Auto"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        {offered.length > 1 && (
          <label className={styles.field}>
            Modulation
            <select
              className={styles.input}
              value={chosen}
              onChange={(event) => setModulation(event.target.value)}
            >
              {offered.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
        )}
        <Button
          variant="primary"
          disabled={isLoading || draft.trim() === "" || isNaN(Number(draft))}
          onClick={async () => {
            if (
              !report(
                "Could not set the frequency",
                await send(Number(draft), chosen),
              )
            ) {
              setDraft(current);
            }
          }}
        >
          Set
        </Button>
        <Button
          disabled={isLoading || radios.frequency_mhz == null}
          onClick={async () =>
            report("Could not reset the frequency", await send(null, null))
          }
        >
          Auto
        </Button>
      </div>
      <p className={styles.hint}>
        Its radio tunes {radios.ranges.map(rangeLabel).join(", ")}. On Auto, the
        flight uses the frequency of its package.
      </p>
      <Warnings warnings={radios.warnings} />
    </section>
  );
}

function PackageFrequency({ packageId, flightId, radios }: FlightProps) {
  const report = useCommandReport();
  const [setFrequency, { isLoading }] = useSetPackageFrequencyMutation();
  const current = text(radios.package_frequency_mhz);
  const [draft, setDraft] = useState(current);
  useEffect(() => setDraft(current), [current]);
  const send = (mhz: number | null) =>
    setFrequency({ packageId, flightId, packageFrequencyJs: { mhz } });

  return (
    <section className={styles.panel} aria-label="Package frequency">
      <h3 className={styles.title}>Package frequency</h3>
      <div className={styles.fields}>
        <label className={styles.field}>
          MHz
          <input
            className={styles.input}
            inputMode="decimal"
            placeholder="Auto"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        <Button
          variant="primary"
          disabled={isLoading || draft.trim() === "" || isNaN(Number(draft))}
          onClick={async () => {
            if (
              !report(
                "Could not set the package frequency",
                await send(Number(draft)),
              )
            ) {
              setDraft(current);
            }
          }}
        >
          Set
        </Button>
        <Button
          disabled={isLoading || radios.package_frequency_mhz == null}
          onClick={async () =>
            report("Could not reset the package frequency", await send(null))
          }
        >
          Auto
        </Button>
      </div>
      <p className={styles.hint}>
        From {radios.package_min_mhz} up to {radios.package_max_mhz} MHz. All
        the flights of the package share it.
      </p>
      <Warnings warnings={radios.package_warnings} />
    </section>
  );
}

function FlightTacan({ packageId, flightId, radios }: FlightProps) {
  const report = useCommandReport();
  const [setTacan, { isLoading }] = useSetFlightTacanMutation();
  const [channel, setChannel] = useState(text(radios.tacan_channel));
  const [band, setBand] = useState(radios.tacan_band ?? "Y");
  const [callsign, setCallsign] = useState(text(radios.tacan_callsign));
  useEffect(() => {
    setChannel(text(radios.tacan_channel));
    setBand(radios.tacan_band ?? "Y");
    setCallsign(text(radios.tacan_callsign));
  }, [radios.tacan_channel, radios.tacan_band, radios.tacan_callsign]);

  return (
    <section className={styles.panel} aria-label="TACAN">
      <h3 className={styles.title}>TACAN</h3>
      <div className={styles.fields}>
        <label className={styles.field}>
          Channel
          <input
            className={styles.input}
            inputMode="numeric"
            placeholder="Auto"
            value={channel}
            onChange={(event) => setChannel(event.target.value)}
          />
        </label>
        <label className={styles.field}>
          Band
          <select
            className={styles.input}
            value={band}
            onChange={(event) => setBand(event.target.value)}
          >
            <option value="X">X</option>
            <option value="Y">Y</option>
          </select>
        </label>
        <label className={styles.field}>
          Callsign
          <input
            className={styles.input}
            maxLength={3}
            value={callsign}
            onChange={(event) => setCallsign(event.target.value)}
          />
        </label>
        <Button
          variant="primary"
          disabled={isLoading || !/^\d+$/.test(channel)}
          onClick={async () =>
            report(
              "Could not set the TACAN",
              await setTacan({
                packageId,
                flightId,
                flightTacanJs: {
                  channel: Number(channel),
                  band,
                  callsign: callsign === "" ? null : callsign,
                },
              }),
            )
          }
        >
          Set
        </Button>
        <Button
          disabled={isLoading || radios.tacan_channel == null}
          onClick={async () =>
            report(
              "Could not reset the TACAN",
              await setTacan({ packageId, flightId, flightTacanJs: {} }),
            )
          }
        >
          Auto
        </Button>
      </div>
      <Warnings warnings={radios.tacan_warnings} />
    </section>
  );
}

function Datalink(props: {
  packageId: string;
  flightId: string;
  datalink: FlightDatalink;
}) {
  const { datalink } = props;
  return (
    <section className={styles.panel} aria-label={datalink.name}>
      <h3 className={styles.title}>{datalink.name}</h3>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Member</th>
            {datalink.fields.map((field) => (
              <th key={field.identifier} scope="col">
                {field.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {datalink.members.map((member) => {
            const name = member.pilot ?? `Aircraft ${member.index + 1}`;
            return (
              <tr key={member.index}>
                <th scope="row">{name}</th>
                {datalink.fields.map((field) => (
                  <td key={field.identifier}>
                    <DatalinkInput
                      packageId={props.packageId}
                      flightId={props.flightId}
                      member={member}
                      memberName={name}
                      field={field}
                    />
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className={styles.hint}>
        Left empty, a value is assigned when the mission is generated.
      </p>
    </section>
  );
}

function DatalinkInput(props: {
  packageId: string;
  flightId: string;
  member: DatalinkMember;
  memberName: string;
  field: DatalinkField;
}) {
  const { member, field } = props;
  const report = useCommandReport();
  const [setValue] = useSetFlightDatalinkMutation();
  const current = member.values[field.identifier] ?? "";
  const [draft, setDraft] = useState(current);
  useEffect(() => setDraft(current), [current]);

  const commit = async () => {
    if (draft === current) {
      return;
    }
    const result = await setValue({
      packageId: props.packageId,
      flightId: props.flightId,
      memberIndex: member.index,
      datalinkValueJs: { identifier: field.identifier, value: draft },
    });
    if (!report(`Could not set the ${field.label}`, result)) {
      setDraft(current);
    }
  };

  return (
    <input
      className={styles.input}
      aria-label={`${field.label} of ${props.memberName}`}
      maxLength={field.max_length}
      placeholder="Auto"
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          commit();
        }
      }}
    />
  );
}

/** The data cartridge of the flight in the last mission, saved where DCS reads it. */
function DataCartridge({ packageId, flightId, radios }: FlightProps) {
  const toast = useToast();
  const report = useCommandReport();
  const [save, { isLoading }] = useSaveFlightCartridgeMutation();
  const onSave = async () => {
    const result = await save({ packageId, flightId });
    if (!report("Could not save the cartridge", result)) return;
    if ("data" in result && result.data.outcome === "saved") {
      toast({ title: "Cartridge saved", description: result.data.path ?? "" });
    }
  };
  return (
    <section className={styles.panel} aria-label="Data cartridge">
      <h3 className={styles.title}>Data cartridge</h3>
      {radios.cartridge_file == null ? (
        <p className={styles.hint}>
          The cartridge comes with the mission (Take off), for a player flight
          of an aircraft that takes one (F/A-18C). It loads at spawn.
        </p>
      ) : (
        <>
          <p className={styles.hint}>
            {radios.cartridge_file}, in the last mission: it loads at spawn.
            Save a copy for the DTC manager of DCS.
          </p>
          <div className={styles.fields}>
            <Button disabled={isLoading} onClick={onSave}>
              Save the cartridge…
            </Button>
          </div>
        </>
      )}
    </section>
  );
}

/** ICLS and Link 4 belong to the base: the panel of the base screen, where it has any. */
function DepartureRadios({ cpId, name }: { cpId: string; name: string }) {
  const { data: actions } = useGetBaseActionsQuery({ cpId });
  if (actions?.radios == null) {
    return null;
  }
  return (
    <RadiosPanel
      cpId={cpId}
      radios={actions.radios}
      title={`Radios of ${name}`}
    />
  );
}
