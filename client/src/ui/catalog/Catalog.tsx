import { SymbolSet } from "../../maplayers/symbology";
import {
  Button,
  Gauge,
  IconButton,
  ListCard,
  MilSymbol,
  Modal,
  ModalClose,
  NumberField,
  SidePanel,
  Slider,
  Switch,
  Table,
  TableColumn,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  TASK_FAMILY_BY_FLIGHT_TYPE,
  TaskTag,
  ToastProvider,
  Tooltip,
  color,
  useToast,
} from "../index";
import styles from "./Catalog.module.css";
import { ReactNode, useState } from "react";

// Dev-only catalog (WEB-00.2): every component in its states, on the tokens.

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={styles.section} aria-label={title}>
      <h2 className={styles.sectionTitle}>{title}</h2>
      {children}
    </section>
  );
}

function GearIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1" />
    </svg>
  );
}

function Colors() {
  return (
    <div className={styles.swatches}>
      {Object.entries(color).map(([name, value]) => (
        <div key={name} className={styles.swatch}>
          <div className={styles.chip} style={{ background: value }} />
          <span>{name}</span>
          <span className={styles.mono}>{value}</span>
        </div>
      ))}
    </div>
  );
}

function Typography() {
  return (
    <div className={styles.type}>
      <p
        style={{
          fontFamily: "var(--ui-font-display)",
          fontSize: "var(--ui-font-size-display)",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "var(--ui-letter-spacing-wide)",
        }}
      >
        Retribution · Barlow Condensed 700
      </p>
      <p
        style={{
          fontFamily: "var(--ui-font-display)",
          fontSize: "var(--ui-font-size-lg)",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "var(--ui-letter-spacing-display)",
        }}
      >
        Section label · Barlow Condensed 600
      </p>
      <p>
        Body text · Inter 400 — the quick brown fox jumps over the lazy dog.
      </p>
      <p
        style={{
          color: "var(--ui-color-text-secondary)",
          fontSize: "var(--ui-font-size-sm)",
        }}
      >
        Secondary text · Inter 12px
      </p>
      <p
        style={{
          fontFamily: "var(--ui-font-mono)",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        JetBrains Mono · 17 MAY 2022 06:40 · 44°57′N 38°59′E · $1 240M
      </p>
    </div>
  );
}

function Buttons() {
  return (
    <div className={styles.stack} style={{ maxWidth: "none" }}>
      <div className={styles.row}>
        <Button variant="primary">Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="danger">Delete package</Button>
        <Button variant="ghost">Ghost</Button>
        <IconButton aria-label="Settings">
          <GearIcon />
        </IconButton>
        <IconButton aria-label="Settings (secondary)" variant="secondary">
          <GearIcon />
        </IconButton>
      </div>
      <div className={styles.row}>
        <Button variant="primary" size="lg">
          Take off
        </Button>
        <Button variant="secondary" size="lg">
          End turn
        </Button>
        <Button variant="primary" disabled>
          Disabled
        </Button>
        <Button variant="danger" disabled>
          Disabled
        </Button>
        <IconButton aria-label="Disabled settings" disabled>
          <GearIcon />
        </IconButton>
      </div>
    </div>
  );
}

function Controls() {
  const [on, setOn] = useState(true);
  const [count, setCount] = useState(12);
  const [budget, setBudget] = useState(300);
  const [range, setRange] = useState(40);
  return (
    <div className={styles.row} style={{ alignItems: "flex-start", gap: 32 }}>
      <div className={styles.stack}>
        <Switch
          label="Allow AI pilot leveling"
          checked={on}
          onCheckedChange={setOn}
        />
        <Switch label="Enable CSAR for the enemy" defaultChecked={false} />
        <Switch label="Disabled (on)" checked disabled />
        <Switch label="Disabled (off)" checked={false} disabled />
      </div>
      <div className={styles.stack}>
        <NumberField
          label="Pilots per squadron"
          value={count}
          onValueChange={setCount}
          min={1}
          max={24}
        />
        <NumberField
          label="AI surplus reserve"
          value={budget}
          onValueChange={setBudget}
          min={0}
          step={10}
          unit="$M"
          hideSteppers
        />
        <NumberField
          label="Disabled"
          value={4}
          onValueChange={() => undefined}
          disabled
        />
      </div>
      <div className={styles.stack} style={{ width: 280 }}>
        <Slider
          label="Threat range"
          value={range}
          onValueChange={setRange}
          format={(v) => `${v} nm`}
        />
        <Slider
          label="Disabled"
          value={60}
          onValueChange={() => undefined}
          disabled
        />
      </div>
    </div>
  );
}

function TasksAndGauges() {
  return (
    <div className={styles.stack} style={{ maxWidth: "none" }}>
      <div className={styles.row}>
        {Object.keys(TASK_FAMILY_BY_FLIGHT_TYPE).map((task) => (
          <TaskTag key={task} task={task} />
        ))}
        <TaskTag task="DEAD" size="lg" />
      </div>
      <div className={styles.stack}>
        <Gauge label="Runway" value={100} valueText="OK" tone="success" />
        <Gauge label="Aircraft" value={10} max={12} tone="friendly" />
        <Gauge label="Ammunition" value={3} max={12} tone="accent" />
        <Gauge label="Enemy SAM" value={45} tone="hostile" valueText="45%" />
        <Gauge label="Hidden label" hideLabel value={70} valueText={null} />
      </div>
    </div>
  );
}

function Cards() {
  const [selected, setSelected] = useState("dead");
  return (
    <div className={styles.stack}>
      <ListCard
        leading={<TaskTag task="DEAD" />}
        title="SA-11 Krasnodar East"
        meta="TOT 07:12"
        subtitle={
          <>
            <span>4 × F-16CM · Player</span>
            <span>2 × F/A-18C</span>
          </>
        }
        selected={selected === "dead"}
        onSelect={() => setSelected("dead")}
      >
        <Gauge
          label="Readiness"
          hideLabel
          value={100}
          tone="success"
          valueText={null}
        />
      </ListCard>
      <ListCard
        leading={<TaskTag task="BARCAP" />}
        title="Krymsk"
        meta="06:40"
        subtitle={
          <>
            <span>2 × MiG-29S</span>
            <span>3 rounds</span>
          </>
        }
        selected={selected === "barcap"}
        onSelect={() => setSelected("barcap")}
      />
      <ListCard
        leading={<TaskTag task="CSAR" />}
        title="Static card"
        subtitle="Not selectable"
      />
      <ListCard
        leading={<TaskTag task="Strike" />}
        title="Disabled"
        onSelect={() => undefined}
        disabled
      />
    </div>
  );
}

interface Squadron {
  id: string;
  name: string;
  aircraft: string;
  task: string;
  pilots: number;
}

const SQUADRONS: Squadron[] = [
  {
    id: "1",
    name: "VFA-87 Golden Warriors",
    aircraft: "F/A-18C",
    task: "Strike",
    pilots: 12,
  },
  {
    id: "2",
    name: "77th FS Gamblers",
    aircraft: "F-16CM",
    task: "SEAD",
    pilots: 9,
  },
  {
    id: "3",
    name: "VAW-125 Tigertails",
    aircraft: "E-2D",
    task: "AEW&C",
    pilots: 4,
  },
];

const COLUMNS: TableColumn<Squadron>[] = [
  {
    key: "name",
    header: "Squadron",
    cell: (s) => s.name,
    sortValue: (s) => s.name,
  },
  { key: "aircraft", header: "Aircraft", cell: (s) => s.aircraft },
  {
    key: "task",
    header: "Primary task",
    cell: (s) => <TaskTag task={s.task} />,
  },
  {
    key: "pilots",
    header: "Pilots",
    cell: (s) => s.pilots,
    align: "end",
    mono: true,
    sortValue: (s) => s.pilots,
  },
];

function Tables() {
  const [selected, setSelected] = useState<string | undefined>("2");
  return (
    <div className={styles.stack} style={{ maxWidth: 720 }}>
      <Table
        caption="Squadrons"
        columns={COLUMNS}
        rows={SQUADRONS}
        rowKey={(s) => s.id}
        onRowClick={(s) => setSelected(s.id)}
        selectedKey={selected}
      />
      <Table
        caption="Empty table"
        columns={COLUMNS}
        rows={[]}
        rowKey={(s) => s.id}
        emptyText="No squadron at this base"
      />
    </div>
  );
}

function Overlays() {
  const toast = useToast();
  return (
    <div className={styles.row}>
      <Modal
        title="Delete package"
        description="SA-11 Krasnodar East and its 2 flights will be removed."
        trigger={<Button variant="danger">Open modal</Button>}
        footer={
          <>
            <ModalClose asChild>
              <Button>Cancel</Button>
            </ModalClose>
            <ModalClose asChild>
              <Button variant="danger">Delete</Button>
            </ModalClose>
          </>
        }
      >
        Pilots return to their squadrons.
      </Modal>
      <Button
        onClick={() =>
          toast({ title: "Turn 05", description: "Mission generated." })
        }
      >
        Info toast
      </Button>
      <Button
        onClick={() =>
          toast({
            title: "Order placed",
            description: "2 × F-16CM arrive next turn.",
            tone: "success",
          })
        }
      >
        Success toast
      </Button>
      <Button
        onClick={() =>
          toast({
            title: "Command failed",
            description: "The server refused the order.",
            tone: "danger",
          })
        }
      >
        Danger toast
      </Button>
      <Tooltip content="Opens the campaign settings">
        <Button variant="ghost">Hover or focus me</Button>
      </Tooltip>
    </div>
  );
}

function Symbols() {
  return (
    <div className={styles.row}>
      <MilSymbol
        label="Friendly fighter"
        affiliation="friend"
        symbolSet={SymbolSet.AIR}
        entity="fighter"
      />
      <MilSymbol
        label="Hostile fighter"
        affiliation="hostile"
        symbolSet={SymbolSet.AIR}
        entity="fighter"
      />
      <MilSymbol
        label="Friendly armor"
        affiliation="friend"
        symbolSet={SymbolSet.LAND_UNIT}
        entity="armor"
      />
      <MilSymbol
        label="Hostile armor"
        affiliation="hostile"
        symbolSet={SymbolSet.LAND_UNIT}
        entity="armor"
      />
      <MilSymbol
        label="Friendly air defense"
        affiliation="friend"
        symbolSet={SymbolSet.LAND_UNIT}
        entity="airDefense"
      />
      <MilSymbol
        label="Hostile air defense"
        affiliation="hostile"
        symbolSet={SymbolSet.LAND_UNIT}
        entity="airDefense"
      />
      <MilSymbol
        label="Friendly carrier"
        affiliation="friend"
        symbolSet={SymbolSet.SEA_SURFACE}
        entity="carrier"
      />
      <MilSymbol
        label="Hostile airbase"
        affiliation="hostile"
        symbolSet={SymbolSet.LAND_INSTALLATIONS}
        entity="airportAirBase"
      />
      <MilSymbol
        label="Unknown radar"
        affiliation="unknown"
        symbolSet={SymbolSet.LAND_EQUIPMENT}
        entity="radar"
        size={48}
      />
    </div>
  );
}

export function Catalog() {
  return (
    <ToastProvider>
      <div className={styles.page}>
        <SidePanel title="Side panel">
          <div className={styles.panelBody}>
            <Tabs defaultValue="packages">
              <TabsList stretch aria-label="Panel tabs">
                <TabsTrigger value="packages">Packages · 7</TabsTrigger>
                <TabsTrigger value="enemy">Enemy ATO</TabsTrigger>
              </TabsList>
              <TabsContent value="packages">
                <p>Collapse me to see the rail (W15, 1366×768).</p>
              </TabsContent>
              <TabsContent value="enemy">
                <p>Enemy packages.</p>
              </TabsContent>
            </Tabs>
          </div>
        </SidePanel>
        <main className={styles.main}>
          <h1 className={styles.heading}>UI catalog</h1>
          <p className={styles.lead}>
            Design system of the web UI (WEB-00.2). Dev only: not part of the
            build.
          </p>
          <Section title="Colours">
            <Colors />
          </Section>
          <Section title="Typography">
            <Typography />
          </Section>
          <Section title="Buttons">
            <Buttons />
          </Section>
          <Section title="Tabs">
            <Tabs defaultValue="general">
              <TabsList aria-label="Settings sections">
                <TabsTrigger value="general">General</TabsTrigger>
                <TabsTrigger value="pilots">Pilots</TabsTrigger>
                <TabsTrigger value="payload">Payload</TabsTrigger>
                <TabsTrigger value="disabled" disabled>
                  Disabled
                </TabsTrigger>
              </TabsList>
              <TabsContent value="general">
                <p>General settings.</p>
              </TabsContent>
              <TabsContent value="pilots">
                <p>Pilot settings.</p>
              </TabsContent>
              <TabsContent value="payload">
                <p>Payload settings.</p>
              </TabsContent>
            </Tabs>
          </Section>
          <Section title="Switch · Number field · Slider">
            <Controls />
          </Section>
          <Section title="Task tags · Gauges">
            <TasksAndGauges />
          </Section>
          <Section title="List cards">
            <Cards />
          </Section>
          <Section title="Table">
            <Tables />
          </Section>
          <Section title="Modal · Toast · Tooltip">
            <Overlays />
          </Section>
          <Section title="Military symbols (APP-6)">
            <Symbols />
          </Section>
          <Section title="Side panel (right)">
            <div className={styles.panelDemo}>
              <div className={styles.mapStub} />
              <SidePanel title="Flight" side="right" defaultOpen={false}>
                <div className={styles.panelBody}>Starts collapsed.</div>
              </SidePanel>
            </div>
          </Section>
        </main>
      </div>
    </ToastProvider>
  );
}
