// Pilots tab of a flight (WEB-04.2): `FlightRosterEditor` of the Qt editor, one row per
// aircraft with its pilot and whether a player flies it.
import {
  FlightPilotSlot,
  FlightSettings,
  useSetFlightPilotMutation,
  useSetFlightSlotPlayerMutation,
} from "../api/liberationApi";
import settingsStyles from "../settings/SettingsScreen.module.css";
import { Switch } from "../ui";
import styles from "./FlightSettings.module.css";
import {
  FlightSettingsLoader,
  FlightTabProps,
  UnderWayNotice,
  useReportRefusal,
} from "./FlightSettingsLoader";

export function FlightPilotsTab({ packageId, flightId }: FlightTabProps) {
  return (
    <FlightSettingsLoader packageId={packageId} flightId={flightId}>
      {(settings) => (
        <div className={styles.tab}>
          <UnderWayNotice settings={settings} />
          <ul className={styles.slots} aria-label="Pilots">
            {settings.slots.map((slot, index) => (
              <SlotRow
                key={index}
                packageId={packageId}
                settings={settings}
                slot={slot}
                index={index}
              />
            ))}
          </ul>
          <p className={styles.hint}>
            Changing a pilot or a player sets the start type back to the default
            of the flight.
          </p>
        </div>
      )}
    </FlightSettingsLoader>
  );
}

function SlotRow({
  packageId,
  settings,
  slot,
  index,
}: {
  packageId: string;
  settings: FlightSettings;
  slot: FlightPilotSlot;
  index: number;
}) {
  const report = useReportRefusal();
  const [setPilot] = useSetFlightPilotMutation();
  const [setPlayer] = useSetFlightSlotPlayerMutation();
  const flight = { packageId, flightId: settings.id, slot: index };
  const pilot = slot.pilot;
  const number = index + 1;

  return (
    <li className={styles.slot}>
      <span className={styles.slotNumber}>{number}</span>
      <select
        aria-label={`Pilot ${number}`}
        className={settingsStyles.select}
        value={pilot?.id ?? ""}
        disabled={!settings.editable}
        onChange={async (event) =>
          report(
            "Could not change the pilot",
            await setPilot({
              ...flight,
              flightPilotChoiceJs: {
                pilot_id: event.target.value || undefined,
              },
            }),
          )
        }
      >
        <option value="">Unassigned</option>
        {pilot != null && <option value={pilot.id}>{pilot.name}</option>}
        {settings.free_pilots.map((free) => (
          <option key={free.id} value={free.id}>
            {free.name}
          </option>
        ))}
      </select>
      <Switch
        label="Player"
        aria-label={`Player ${number}`}
        title={slot.player_refusal ?? undefined}
        checked={pilot?.player ?? false}
        disabled={
          !settings.editable || pilot == null || slot.player_refusal != null
        }
        onCheckedChange={async (player) =>
          report(
            "Could not change the player",
            await setPlayer({ ...flight, flightSlotPlayerJs: { player } }),
          )
        }
      />
    </li>
  );
}
