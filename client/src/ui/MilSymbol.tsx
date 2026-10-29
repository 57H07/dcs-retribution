import {
  EntityKey,
  Status,
  StandardIdentity,
  SymbolSet,
  sidc as buildSidc,
} from "../maplayers/symbology";
import { color } from "./tokens";
import ms from "milsymbol";
import { useMemo } from "react";

// APP-6 symbols drawn by milsymbol (W14). Friend and hostile differ by frame
// shape (rectangle / diamond for land, arcs for air), not only by colour; the
// fill colours come from the tokens so symbols match the rest of the UI.

export type Affiliation = "friend" | "hostile" | "unknown";

const IDENTITY: Record<Affiliation, StandardIdentity> = {
  friend: StandardIdentity.FRIEND,
  hostile: StandardIdentity.HOSTILE_FAKER,
  unknown: StandardIdentity.UNKNOWN,
};

const FILL = ms.ColorMode(
  "#C7B3E6", // civilian
  color.friendly,
  color.hostile,
  color.success, // neutral
  color.accentHover, // unknown
  color.hostile, // suspect
);

interface CommonProps {
  /** Accessible name, e.g. "Friendly fighter, Krymsk". */
  label: string;
  /** Height of the symbol body in pixels. */
  size?: number;
  className?: string;
}

interface FromSidc extends CommonProps {
  /** A 20-digit SIDC, as sent by the backend (game/sidc.py). */
  sidc: string;
}

interface FromParts extends CommonProps {
  affiliation: Affiliation;
  symbolSet: SymbolSet;
  entity: EntityKey;
  status?: Status;
}

export type MilSymbolProps = FromSidc | FromParts;

export function sidcFor(props: MilSymbolProps): string {
  if ("sidc" in props) {
    return props.sidc;
  }
  return buildSidc(
    IDENTITY[props.affiliation],
    props.symbolSet,
    props.entity,
    props.status,
  );
}

export function MilSymbol(props: MilSymbolProps) {
  const { label, size = 32, className } = props;
  const code = sidcFor(props);
  const src = useMemo(
    () => new ms.Symbol(code, { size, colorMode: FILL }).toDataURL(),
    [code, size],
  );
  return (
    <img
      className={className}
      src={src}
      alt={label}
      data-sidc={code}
      style={{ display: "inline-block", verticalAlign: "middle" }}
    />
  );
}
