import { LAYER_COLORS } from "../../maplayers/colors";
import {
  OverlayId,
  defaultActiveOverlays,
  overlayIdForName,
} from "../../maplayers/overlays";
import { symbolDataUrl } from "../../maplayers/symbology";
import "./Legend.css";
import { LegendSwatch, visibleSections } from "./legendEntries";
import { DomEvent, LayersControlEvent } from "leaflet";
import { useEffect, useRef, useState } from "react";
import { useMapEvents } from "react-leaflet";

export const LEGEND_OPEN_STORAGE_KEY = "retribution.map.legendOpen";

function readOpenState(): boolean {
  try {
    return window.localStorage.getItem(LEGEND_OPEN_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function writeOpenState(open: boolean) {
  try {
    window.localStorage.setItem(LEGEND_OPEN_STORAGE_KEY, String(open));
  } catch {
    // Storage unavailable: the state is simply not remembered.
  }
}

const SWATCH_WIDTH = 28;
const SWATCH_HEIGHT = 16;

function Swatch(props: { swatch: LegendSwatch }) {
  const swatch = props.swatch;
  if (swatch.kind === "symbol") {
    return (
      <img
        className="legend-symbol"
        src={symbolDataUrl(swatch.sidc, swatch.style)}
        alt=""
      />
    );
  }
  const mid = SWATCH_HEIGHT / 2;
  let shape;
  switch (swatch.kind) {
    case "line":
      shape = (
        <>
          <line
            x1={2}
            y1={mid}
            x2={SWATCH_WIDTH - 2}
            y2={mid}
            stroke={LAYER_COLORS[swatch.color]}
            strokeWidth={swatch.weight}
            strokeOpacity={swatch.opacity ?? 1}
            strokeDasharray={swatch.dashArray}
          />
          {swatch.overlay && (
            <line
              x1={2}
              y1={mid}
              x2={SWATCH_WIDTH - 2}
              y2={mid}
              stroke={LAYER_COLORS[swatch.overlay.color]}
              strokeWidth={swatch.overlay.weight}
            />
          )}
        </>
      );
      break;
    case "ring":
      shape = (
        <circle
          cx={SWATCH_WIDTH / 2}
          cy={mid}
          r={mid - 2}
          fill="none"
          stroke={LAYER_COLORS[swatch.color]}
          strokeWidth={swatch.weight}
        />
      );
      break;
    case "area":
      shape = (
        <rect
          x={3}
          y={2}
          width={SWATCH_WIDTH - 6}
          height={SWATCH_HEIGHT - 4}
          fill={LAYER_COLORS[swatch.color]}
          fillOpacity={swatch.fillOpacity}
          stroke={LAYER_COLORS[swatch.color]}
          strokeWidth={1}
        />
      );
      break;
  }
  return (
    <svg
      className="legend-swatch"
      width={SWATCH_WIDTH}
      height={SWATCH_HEIGHT}
      viewBox={`0 0 ${SWATCH_WIDTH} ${SWATCH_HEIGHT}`}
      aria-hidden
    >
      {shape}
    </svg>
  );
}

interface LegendPanelProps {
  active: Set<OverlayId>;
}

export function LegendPanel(props: LegendPanelProps) {
  const sections = visibleSections(props.active);
  if (sections.length === 0) {
    return <p className="legend-empty">No active layer.</p>;
  }
  return (
    <div className="legend-panel">
      {sections.map((section) => (
        <section key={section.title} className="legend-section">
          <h3>{section.title}</h3>
          <ul>
            {section.entries.map((entry) => (
              <li key={entry.label}>
                <span className="legend-swatch-cell">
                  <Swatch swatch={entry.swatch} />
                </span>
                <span>{entry.label}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

// Legend button and collapsible panel, positioned like a Leaflet control. The
// open state is remembered across sessions.
export function LegendControl(props: LegendPanelProps) {
  const [open, setOpen] = useState(readOpenState);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Clicks and scrolls in the legend must not pan or zoom the map.
    if (container.current) {
      DomEvent.disableClickPropagation(container.current);
      DomEvent.disableScrollPropagation(container.current);
    }
  }, []);

  const toggle = () => {
    setOpen(!open);
    writeOpenState(!open);
  };

  return (
    <div className="leaflet-bottom leaflet-right">
      <div className="leaflet-control leaflet-bar legend" ref={container}>
        <button
          type="button"
          className="legend-toggle"
          aria-expanded={open}
          onClick={toggle}
        >
          Legend
        </button>
        {open && <LegendPanel active={props.active} />}
      </div>
    </div>
  );
}

// Tracks which overlays of the layer controls are on the map. Starts from the
// overlays enabled by default, then follows the layer control events.
export function useActiveOverlays(): Set<OverlayId> {
  const [active, setActive] = useState(defaultActiveOverlays);
  const update = (name: string, on: boolean) => {
    const id = overlayIdForName(name);
    if (id === undefined) {
      return;
    }
    setActive((current) => {
      if (current.has(id) === on) {
        return current;
      }
      const next = new Set(current);
      if (on) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  };
  useMapEvents({
    overlayadd: (e: LayersControlEvent) => update(e.name, true),
    overlayremove: (e: LayersControlEvent) => update(e.name, false),
  });
  return active;
}

export default function Legend() {
  const active = useActiveOverlays();
  return <LegendControl active={active} />;
}
