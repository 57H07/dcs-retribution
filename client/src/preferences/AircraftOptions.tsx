// The options of an aircraft list: the player's modules first, marked, then the
// others. Which aircraft are the player's comes from the server.
import styles from "./Preferences.module.css";

export interface AircraftOption {
  id: string;
  name: string;
  playerModule: boolean;
  /** Squadrons of this aircraft already in the air wing, when that matters. */
  squadrons?: number;
}

function Option({ option }: { option: AircraftOption }) {
  const mark = option.playerModule ? "★ " : "";
  const count = option.squadrons ? ` · ${option.squadrons}` : "";
  return (
    <option value={option.id}>
      {mark}
      {option.name}
      {count}
    </option>
  );
}

export function AircraftOptions({
  options,
  grouped = true,
}: {
  options: AircraftOption[];
  /** False for the enemy side, where no aircraft is the player's. */
  grouped?: boolean;
}) {
  const own = options.filter((o) => o.playerModule);
  const others = options.filter((o) => !o.playerModule);
  const render = (list: AircraftOption[]) =>
    list.map((o) => <Option key={o.id} option={o} />);
  if (!grouped || own.length === 0) {
    return <>{render(options)}</>;
  }
  return (
    <>
      <optgroup label="Your modules">{render(own)}</optgroup>
      {others.length > 0 && (
        <optgroup label="AI only">{render(others)}</optgroup>
      )}
    </>
  );
}

export function NoModulesHint() {
  return (
    <span className={styles.note}>
      None of your modules here. Declare the modules you own in File →
      Preferences.
    </span>
  );
}
