// "Radios & TACAN" tab of a flight (WEB-04.5): the frequency of the flight and of its
// package, a tanker's TACAN, the datalink of each member, and what belongs to the
// departure base (ICLS, Link 4), edited with the panel of the base screen. Changes
// apply at once, each command answers the whole tab; the server enforces the limits and
// says what is worth a warning. The data cartridge of the last mission (#191) is saved
// from here, through the native save dialog, and what goes into the cartridges of the
// flight's squadron is set here (#221): kept on the squadron, checked by the server.
import { commandErrorMessage } from "../api/commands";
import {
  CartridgeSettings,
  CmdsField,
  DatalinkField,
  DatalinkMember,
  FlightDatalink,
  FlightRadios,
  RadioRange,
  useApplyCartridgeSettingsToAircraftMutation,
  useGetBaseActionsQuery,
  useResetCartridgeSettingsMutation,
  useGetFlightRadiosQuery,
  useSaveFlightCartridgeMutation,
  useSetCartridgeSettingsMutation,
  useSetFlightDatalinkMutation,
  useSetFlightFrequencyMutation,
  useSetFlightTacanMutation,
  useSetPackageFrequencyMutation,
} from "../api/liberationApi";
import { RadiosPanel } from "../bases/BaseActionsPanels";
import { Button, Switch, useToast } from "../ui";
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
  const settings = radios.cartridge_settings;
  return (
    <section className={styles.panel} aria-label="Data cartridge">
      <h3 className={styles.title}>Data cartridge</h3>
      {radios.cartridge_file == null ? (
        <p className={styles.hint}>
          The cartridge comes with the mission (Take off), for a player flight
          of an aircraft that takes one (F/A-18C, F-16C, F-14B upgrade, AH-64D).
        </p>
      ) : (
        <>
          <p className={styles.hint}>
            {radios.cartridge_file}, in the last mission. Save a copy for the
            DTC manager of DCS.
          </p>
          <div className={styles.fields}>
            <Button disabled={isLoading} onClick={onSave}>
              Save the cartridge…
            </Button>
          </div>
        </>
      )}
      {settings != null && (
        <CartridgeSettingsPanel
          packageId={packageId}
          flightId={flightId}
          settings={settings}
        />
      )}
    </section>
  );
}

function isDefault(settings: CartridgeSettings): boolean {
  return (
    settings.auto_load &&
    settings.threats !== false &&
    settings.jdam_targets !== false &&
    !settings.cmds_modified
  );
}

/** What goes into the cartridges of the squadron (#221). */
function CartridgeSettingsPanel(props: {
  packageId: string;
  flightId: string;
  settings: CartridgeSettings;
}) {
  const { packageId, flightId, settings } = props;
  const toast = useToast();
  const report = useCommandReport();
  const [setSettings, { isLoading: setting }] =
    useSetCartridgeSettingsMutation();
  const [reset, { isLoading: resetting }] = useResetCartridgeSettingsMutation();
  const [apply, { isLoading: applying }] =
    useApplyCartridgeSettingsToAircraftMutation();
  const busy = setting || resetting || applying;
  const others = settings.same_aircraft_squadrons;

  const send = async (update: {
    auto_load?: boolean;
    threats?: boolean;
    jdam_targets?: boolean;
  }) =>
    report(
      "Could not set the cartridge",
      await setSettings({
        packageId,
        flightId,
        cartridgeSettingsUpdateJs: update,
      }),
    );

  return (
    <>
      <p className={styles.hint}>
        For every player flight of {settings.squadron}, this turn and the next.
      </p>
      <div className={styles.fields}>
        <Switch
          label="Load at spawn"
          checked={settings.auto_load}
          disabled={busy}
          onCheckedChange={(checked) => send({ auto_load: checked })}
        />
        {settings.threats != null && (
          <Switch
            label="Front lines and enemy air defenses"
            checked={settings.threats}
            disabled={busy}
            onCheckedChange={(checked) => send({ threats: checked })}
          />
        )}
        {settings.jdam_targets != null && (
          <Switch
            label="JDAM targets"
            checked={settings.jdam_targets}
            disabled={busy}
            onCheckedChange={(checked) => send({ jdam_targets: checked })}
          />
        )}
      </div>
      {settings.jdam_targets && (
        <p className={styles.hint}>
          Each station with a JDAM gets the aim points of the package target,
          with the release of the leg into it.
        </p>
      )}
      {!settings.auto_load && (
        <p className={styles.hint}>
          The pilot loads the cartridge from the DTC page of the jet.
        </p>
      )}
      {settings.cmds_fields.length > 0 && (
        <CmdsPrograms
          packageId={packageId}
          flightId={flightId}
          settings={settings}
        />
      )}
      <div className={styles.fields}>
        <Button
          disabled={busy || others === 0}
          onClick={async () => {
            const result = await apply({ packageId, flightId });
            if (report("Could not apply the cartridge", result)) {
              toast({
                title: "Cartridge applied",
                description: `${others} other ${settings.aircraft} squadron${
                  others === 1 ? "" : "s"
                } now use these settings.`,
              });
            }
          }}
        >
          Apply to every {settings.aircraft} squadron
        </Button>
        <Button
          disabled={busy || isDefault(settings)}
          onClick={async () =>
            report(
              "Could not reset the cartridge",
              await reset({ packageId, flightId }),
            )
          }
        >
          Module defaults
        </Button>
      </div>
    </>
  );
}

type Drafts = Record<string, Record<string, string>>;

function draftsOf(settings: CartridgeSettings): Drafts {
  return Object.fromEntries(
    settings.cmds_programs.map((program) => [
      program.id,
      Object.fromEntries(
        Object.entries(program.values).map(([field, value]) => [
          field,
          `${value}`,
        ]),
      ),
    ]),
  );
}

/** The countermeasure programs, edited as a table and sent whole. */
function CmdsPrograms(props: {
  packageId: string;
  flightId: string;
  settings: CartridgeSettings;
}) {
  const { settings } = props;
  const report = useCommandReport();
  const [setSettings, { isLoading }] = useSetCartridgeSettingsMutation();
  const currentKey = JSON.stringify(draftsOf(settings));
  const [drafts, setDrafts] = useState<Drafts>(() => JSON.parse(currentKey));
  useEffect(() => setDrafts(JSON.parse(currentKey)), [currentKey]);

  const changed = JSON.stringify(drafts) !== currentKey;
  const invalid = Object.values(drafts).some((fields) =>
    Object.values(fields).some((v) => v.trim() === "" || isNaN(Number(v))),
  );
  const onSave = async () => {
    const cmds = Object.fromEntries(
      Object.entries(drafts).map(([program, fields]) => [
        program,
        Object.fromEntries(
          Object.entries(fields).map(([field, v]) => [field, Number(v)]),
        ),
      ]),
    );
    const result = await setSettings({
      packageId: props.packageId,
      flightId: props.flightId,
      cartridgeSettingsUpdateJs: { cmds },
    });
    report("Could not set the CMDS programs", result);
  };
  const edit = (program: string, field: string, value: string) =>
    setDrafts((previous) => ({
      ...previous,
      [program]: { ...previous[program], [field]: value },
    }));

  return (
    <div className={styles.cmds}>
      <h4 className={styles.subtitle}>CMDS programs</h4>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Program</th>
            {settings.cmds_fields.map((field) => (
              <th key={field.id} scope="col">
                {field.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {settings.cmds_programs.map((program) => (
            <tr key={program.id}>
              <th scope="row">{program.label}</th>
              {settings.cmds_fields.map((field) => (
                <td key={field.id}>
                  <CmdsInput
                    field={field}
                    program={program.label}
                    value={drafts[program.id]?.[field.id] ?? ""}
                    onChange={(value) => edit(program.id, field.id, value)}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className={styles.fields}>
        <Button
          variant="primary"
          disabled={isLoading || !changed || invalid}
          onClick={onSave}
        >
          Set the programs
        </Button>
        <Button
          disabled={isLoading || !changed}
          onClick={() => setDrafts(JSON.parse(currentKey))}
        >
          Undo
        </Button>
      </div>
      <p className={styles.hint}>
        Starts from the programs of the module. The bingo and threat tables keep
        their defaults.
      </p>
    </div>
  );
}

function CmdsInput(props: {
  field: CmdsField;
  program: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const { field } = props;
  return (
    <input
      className={styles.cmdsInput}
      aria-label={`${field.label} of ${props.program}`}
      type="number"
      inputMode="decimal"
      min={field.minimum}
      max={field.maximum}
      step={field.step}
      value={props.value}
      onChange={(event) => props.onChange(event.target.value)}
    />
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
