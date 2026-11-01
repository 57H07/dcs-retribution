// General tab of a flight (WEB-04.2): what `QGeneralFlightSettingsTab` edits, except the
// radios (Radios & TACAN tab). Each change is a command that applies at once.
import {
  FlightSettings,
  StartType,
  useResetFlightCallsignMutation,
  useSetFlightCallsignMutation,
  useSetFlightCustomNameMutation,
  useSetFlightDivertMutation,
  useSetFlightSizeMutation,
  useSetFlightSquadronMutation,
  useSetFlightStartTypeMutation,
  useSetFlightTotOffsetMutation,
} from "../api/liberationApi";
import { formatTot } from "../command/packages/packageFormat";
import settingsStyles from "../settings/SettingsScreen.module.css";
import { NumberField } from "../ui";
import styles from "./FlightSettings.module.css";
import {
  FlightSettingsLoader,
  FlightTabProps,
  UnderWayNotice,
  useReportRefusal,
} from "./FlightSettingsLoader";
import { useEffect, useState } from "react";

export interface FlightGeneralTabProps extends FlightTabProps {
  /** A squadron change replaces the flight, which gets another id. */
  onFlightReplaced?: (flightId: string) => void;
}

export function FlightGeneralTab({
  packageId,
  flightId,
  onFlightReplaced,
}: FlightGeneralTabProps) {
  return (
    <FlightSettingsLoader packageId={packageId} flightId={flightId}>
      {(settings) => (
        <div className={styles.tab}>
          <UnderWayNotice settings={settings} />
          <dl className={styles.facts}>
            <dt>Task</dt>
            <dd>{settings.task}</dd>
            <dt>Type</dt>
            <dd>{settings.aircraft}</dd>
            <dt>Departure</dt>
            <dd>
              {settings.departure} at {formatTot(settings.startup)}
            </dd>
            <dt>Arrival</dt>
            <dd>{settings.arrival}</dd>
          </dl>
          <div className={styles.grid}>
            <SquadronField
              packageId={packageId}
              settings={settings}
              onFlightReplaced={onFlightReplaced}
            />
            <SizeField packageId={packageId} settings={settings} />
            <StartTypeField packageId={packageId} settings={settings} />
            <DivertField packageId={packageId} settings={settings} />
            <NameField packageId={packageId} settings={settings} />
            <CallsignField packageId={packageId} settings={settings} />
            <TotOffsetField packageId={packageId} settings={settings} />
          </div>
        </div>
      )}
    </FlightSettingsLoader>
  );
}

interface FieldProps {
  packageId: string;
  settings: FlightSettings;
}

function SquadronField({
  packageId,
  settings,
  onFlightReplaced,
}: FieldProps & Pick<FlightGeneralTabProps, "onFlightReplaced">) {
  const report = useReportRefusal();
  const [change, state] = useSetFlightSquadronMutation();

  const select = async (squadronId: string) => {
    const result = await change({
      packageId,
      flightId: settings.id,
      flightSquadronChoiceJs: { squadron_id: squadronId },
    });
    report("Could not change the squadron", result);
    if ("data" in result && result.data !== undefined) {
      onFlightReplaced?.(result.data.flight_id);
    }
  };

  return (
    <div className={styles.fieldBlock}>
      <label className={styles.field}>
        Squadron
        <select
          className={settingsStyles.select}
          value={settings.squadron.id}
          disabled={
            !settings.editable ||
            settings.squadron_options.length === 0 ||
            state.isLoading
          }
          onChange={(event) => select(event.target.value)}
        >
          {[settings.squadron, ...settings.squadron_options].map((squadron) => (
            <option key={squadron.id} value={squadron.id}>
              {squadron.base}: {squadron.name} · {squadron.aircraft} (
              {squadron.available} available)
            </option>
          ))}
        </select>
      </label>
      <p className={styles.hint}>
        Another squadron replans the flight, with new pilots and its default
        loadout.
      </p>
    </div>
  );
}

function SizeField({ packageId, settings }: FieldProps) {
  const report = useReportRefusal();
  const [setSize] = useSetFlightSizeMutation();
  return (
    <NumberField
      label="Size"
      value={settings.count}
      min={1}
      max={settings.max_count}
      disabled={!settings.editable}
      onValueChange={async (size) =>
        report(
          "Could not resize the flight",
          await setSize({
            packageId,
            flightId: settings.id,
            flightSizeJs: { size },
          }),
        )
      }
    />
  );
}

function StartTypeField({ packageId, settings }: FieldProps) {
  const report = useReportRefusal();
  const [setStartType] = useSetFlightStartTypeMutation();
  return (
    <div className={styles.fieldBlock}>
      <label className={styles.field}>
        Start type
        <select
          className={settingsStyles.select}
          value={settings.start_type}
          disabled={!settings.editable || settings.start_type_locked}
          onChange={async (event) =>
            report(
              "Could not change the start type",
              await setStartType({
                packageId,
                flightId: settings.id,
                flightStartTypeJs: {
                  start_type: event.target.value as StartType,
                },
              }),
            )
          }
        >
          {settings.start_types.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </label>
      <p className={styles.hint}>
        Any start other than Cold makes this flight non-targetable by
        OCA/Aircraft missions, which affects game balance.
      </p>
    </div>
  );
}

function DivertField({ packageId, settings }: FieldProps) {
  const report = useReportRefusal();
  const [setDivert] = useSetFlightDivertMutation();
  return (
    <label className={styles.field}>
      Divert
      <select
        className={settingsStyles.select}
        value={settings.divert_id ?? ""}
        disabled={!settings.editable}
        onChange={async (event) =>
          report(
            "Could not change the divert field",
            await setDivert({
              packageId,
              flightId: settings.id,
              flightDivertJs: { divert_id: event.target.value || undefined },
            }),
          )
        }
      >
        <option value="">None</option>
        {settings.divert_options.map((cp) => (
          <option key={cp.id} value={cp.id}>
            {cp.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function NameField({ packageId, settings }: FieldProps) {
  const report = useReportRefusal();
  const [rename] = useSetFlightCustomNameMutation();
  const current = settings.custom_name ?? "";
  const [draft, setDraft] = useState(current);

  useEffect(() => setDraft(current), [current]);

  const commit = async () => {
    if (draft === current) {
      return;
    }
    const result = await rename({
      packageId,
      flightId: settings.id,
      flightCustomNameJs: { name: draft },
    });
    report("Could not rename the flight", result);
    if ("error" in result) {
      setDraft(current);
    }
  };

  return (
    <label className={styles.field}>
      Custom name
      <input
        className={styles.input}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            commit();
          }
        }}
      />
    </label>
  );
}

function CallsignField({ packageId, settings }: FieldProps) {
  const report = useReportRefusal();
  const [setCallsign] = useSetFlightCallsignMutation();
  const [resetCallsign] = useResetFlightCallsignMutation();
  const callsign = settings.callsign;
  const flight = { packageId, flightId: settings.id };

  const send = async (name: string, number: number) =>
    report(
      "Could not set the callsign",
      await setCallsign({ ...flight, flightCallsignJs: { name, number } }),
    );

  return (
    <div className={styles.callsign}>
      <label className={styles.field}>
        Callsign
        <select
          className={settingsStyles.select}
          value={callsign?.name ?? ""}
          onChange={async (event) => {
            if (event.target.value === "") {
              report(
                "Could not reset the callsign",
                await resetCallsign(flight),
              );
            } else {
              await send(
                event.target.value,
                callsign?.number ?? settings.callsign_min_number,
              );
            }
          }}
        >
          <option value="">Automatic</option>
          {settings.callsign_names.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
      <NumberField
        label="Number"
        hideSteppers
        value={callsign?.number ?? settings.callsign_min_number}
        min={settings.callsign_min_number}
        max={settings.callsign_max_number}
        disabled={callsign == null}
        onValueChange={(number) => {
          if (callsign != null) {
            send(callsign.name, number);
          }
        }}
      />
    </div>
  );
}

function TotOffsetField({ packageId, settings }: FieldProps) {
  const report = useReportRefusal();
  const [setOffset] = useSetFlightTotOffsetMutation();
  const total = Math.abs(settings.tot_offset_seconds);
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  const ahead = settings.tot_offset_seconds < 0;

  const send = async (newMinutes: number, newSeconds: number, sign: boolean) =>
    report(
      "Could not change the TOT offset",
      await setOffset({
        packageId,
        flightId: settings.id,
        flightTotOffsetJs: {
          seconds: (sign ? -1 : 1) * (newMinutes * 60 + newSeconds),
        },
      }),
    );

  return (
    <fieldset className={styles.offset}>
      <legend className={styles.legend}>TOT offset from the package</legend>
      <NumberField
        label="Minutes"
        value={minutes}
        min={0}
        max={59}
        disabled={!settings.editable}
        onValueChange={(value) => send(value, seconds, ahead)}
      />
      <NumberField
        label="Seconds"
        value={seconds}
        min={0}
        max={59}
        disabled={!settings.editable}
        onValueChange={(value) => send(minutes, value, ahead)}
      />
      <label className={styles.check}>
        <input
          type="checkbox"
          checked={ahead}
          disabled={!settings.editable}
          onChange={(event) => send(minutes, seconds, event.target.checked)}
        />
        Ahead of package
      </label>
    </fieldset>
  );
}
