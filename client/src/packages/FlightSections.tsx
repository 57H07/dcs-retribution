// Tab frame of a flight in the package editor (mockups/Package.dc.html). Each tab is
// a slot that a lot fills: General and Pilots are done (WEB-04.2), Payload WEB-04.3,
// Route WEB-04.4, Radios & TACAN WEB-04.5. Until then the Qt editor keeps those features:
// replace a tab's <QtEditorSlot> with its screen and remove the slot with the last.
import { PackageEditorFlight } from "../api/liberationApi";
import { useQtCommands } from "../shell/useQtCommands";
import { Button, Tabs, TabsContent, TabsList, TabsTrigger } from "../ui";
import { FlightGeneralTab } from "./FlightGeneralTab";
import { FlightPilotsTab } from "./FlightPilotsTab";
import styles from "./PackageEditor.module.css";
import { ReactNode } from "react";

export const FLIGHT_SECTIONS = [
  { id: "general", label: "General" },
  { id: "route", label: "Route" },
  { id: "payload", label: "Payload" },
  { id: "pilots", label: "Pilots" },
  { id: "radios", label: "Radios & TACAN" },
] as const;

export interface FlightSectionsProps {
  packageId: string;
  flight: PackageEditorFlight;
  /** A squadron change replaces the flight, which gets another id. */
  onFlightReplaced?: (flightId: string) => void;
  /** Right of the tabs: what acts on the whole flight. */
  actions?: ReactNode;
}

export function FlightSections({
  packageId,
  flight,
  onFlightReplaced,
  actions,
}: FlightSectionsProps) {
  return (
    <Tabs className={styles.sections} defaultValue="general">
      <div className={styles.sectionsHeader}>
        <TabsList aria-label="Flight sections">
          {FLIGHT_SECTIONS.map((section) => (
            <TabsTrigger key={section.id} value={section.id}>
              {section.label}
            </TabsTrigger>
          ))}
        </TabsList>
        <span className={styles.spacer} />
        {actions}
      </div>
      <TabsContent value="general" className={styles.section}>
        <FlightGeneralTab
          packageId={packageId}
          flightId={flight.id}
          onFlightReplaced={onFlightReplaced}
        />
      </TabsContent>
      <TabsContent value="route" className={styles.section}>
        <QtEditorSlot flight={flight} what="The route" />
      </TabsContent>
      <TabsContent value="payload" className={styles.section}>
        <QtEditorSlot flight={flight} what="The payload" />
      </TabsContent>
      <TabsContent value="pilots" className={styles.section}>
        <FlightPilotsTab packageId={packageId} flightId={flight.id} />
      </TabsContent>
      <TabsContent value="radios" className={styles.section}>
        <QtEditorSlot flight={flight} what="Radios and TACAN" />
      </TabsContent>
    </Tabs>
  );
}

function QtEditorSlot({
  flight,
  what,
}: {
  flight: PackageEditorFlight;
  what: string;
}) {
  const qt = useQtCommands();
  return (
    <div className={styles.slot}>
      <p className={styles.hint}>{what}: not in the web editor yet.</p>
      <Button onClick={() => qt.editPackageOfFlight(flight.id)}>
        Open the Qt editor
      </Button>
    </div>
  );
}
