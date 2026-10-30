// Command view (WEB-01.1): packages panel on the left, map in the centre with
// the turn actions, inspector on the right, mission timeline at the bottom.
// The panels are slots: WEB-01.2 fills the left one, WEB-01.3 the inspector,
// WEB-01.4 the timeline. Both side panels collapse to a rail (W15, 1366x768).
import { Button, SidePanel } from "../ui";
import styles from "./CommandView.module.css";
import { MissionTimeline } from "./MissionTimeline";
import { TurnActions } from "./TurnActions";
import { ReactNode, useId, useState } from "react";

export interface CommandViewProps {
  /** The map, always mounted. */
  map: ReactNode;
  packages?: ReactNode;
  inspector?: ReactNode;
  timeline?: ReactNode;
  /** Opens the Qt packages panel until WEB-01.2 replaces it. */
  onOpenPackages?: () => void;
}

export function CommandView({
  map,
  packages,
  inspector,
  timeline,
  onOpenPackages,
}: CommandViewProps) {
  const [timelineOpen, setTimelineOpen] = useState(true);
  const timelineId = useId();
  return (
    <div className={styles.view}>
      <SidePanel title="Packages" side="left" className={styles.side}>
        {packages ?? (
          <div className={styles.empty}>
            <p>The packages of the turn open in their own window for now.</p>
            {onOpenPackages && (
              <Button onClick={onOpenPackages}>Open packages</Button>
            )}
          </div>
        )}
      </SidePanel>
      <div className={styles.center}>
        <div className={styles.map}>
          {map}
          <div className={styles.turnActions}>
            <TurnActions />
          </div>
        </div>
        <section
          className={styles.timeline}
          aria-label="Mission timeline"
          data-state={timelineOpen ? "open" : "closed"}
        >
          <div className={styles.timelineHeader}>
            <span className={styles.timelineTitle}>Timeline</span>
            <Button
              variant="ghost"
              aria-expanded={timelineOpen}
              aria-controls={timelineId}
              onClick={() => setTimelineOpen(!timelineOpen)}
            >
              {timelineOpen ? "Hide" : "Show"}
            </Button>
          </div>
          <div id={timelineId} hidden={!timelineOpen}>
            {timeline ?? <MissionTimeline />}
          </div>
        </section>
      </div>
      <SidePanel
        title="Inspector"
        side="right"
        defaultOpen={false}
        className={styles.side}
      >
        {inspector ?? (
          <p className={styles.empty}>
            Select a base or a site on the map to inspect it.
          </p>
        )}
      </SidePanel>
    </div>
  );
}
