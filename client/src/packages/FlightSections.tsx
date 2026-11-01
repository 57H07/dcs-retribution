// Tab frame of a flight in the package editor (mockups/Package.dc.html); each tab has
// its own screen.
import { PackageEditorFlight } from "../api/liberationApi";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui";
import { FlightGeneralTab } from "./FlightGeneralTab";
import { FlightPilotsTab } from "./FlightPilotsTab";
import { FlightRadiosTab } from "./FlightRadiosTab";
import styles from "./PackageEditor.module.css";
import { RouteTab } from "./route/RouteTab";
import { PayloadTab } from "./PayloadTab";
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
        <RouteTab flightId={flight.id} />
      </TabsContent>
      <TabsContent value="payload" className={styles.section}>
        <PayloadTab packageId={packageId} flightId={flight.id} />
      </TabsContent>
      <TabsContent value="pilots" className={styles.section}>
        <FlightPilotsTab packageId={packageId} flightId={flight.id} />
      </TabsContent>
      <TabsContent value="radios" className={styles.section}>
        <FlightRadiosTab flightId={flight.id} />
      </TabsContent>
    </Tabs>
  );
}
