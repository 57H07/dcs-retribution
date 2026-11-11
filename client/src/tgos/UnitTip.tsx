// A unit name that says what the unit is (#214): on hover or focus, its picture,
// role and job in the campaign; a click opens the full unit sheet (WEB-08.3).
import { useGetUnitInfoQuery } from "../api/liberationApi";
import { PATHS, UnitKind } from "../shell/paths";
import { Tooltip } from "../ui";
import { unitBannerUrl } from "./UnitInfoScreen";
import styles from "./UnitTip.module.css";
import { Link } from "react-router-dom";

/** Fetched when the tooltip opens: Radix mounts its content only then. */
function UnitTipContent({ kind, name }: { kind: UnitKind; name: string }) {
  const { data: info, isError } = useGetUnitInfoQuery({ kind, name });
  if (isError) {
    return <span>No details for this unit.</span>;
  }
  if (!info) {
    return <span>Loading…</span>;
  }
  return (
    <span className={styles.tip}>
      <img
        className={styles.banner}
        src={unitBannerUrl(info.kind, info.name)}
        alt={info.display_name}
      />
      <strong>{info.role}</strong>
      {info.purpose !== "" && (
        <span className={styles.purpose}>{info.purpose}</span>
      )}
      {info.description !== "" && (
        <span className={styles.description}>{info.description}</span>
      )}
      <span className={styles.more}>Click for the full sheet.</span>
    </span>
  );
}

export function UnitTip({
  kind,
  name,
  label,
}: {
  kind: UnitKind;
  /** The unit type's variant id. */
  name: string;
  label: string;
}) {
  return (
    <Tooltip side="right" content={<UnitTipContent kind={kind} name={name} />}>
      <Link className={styles.name} to={PATHS.unit(kind, name)}>
        {label}
      </Link>
    </Tooltip>
  );
}
