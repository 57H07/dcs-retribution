// Reports screen (WEB-08.1, W11): the Qt Intel, Stats and Finances windows as
// three tabs. The engine computes every figure (GET /reports/*): this screen
// only lays them out.
import { PATHS, REPORT_TABS, ReportTab } from "../shell/paths";
import settings from "../settings/SettingsScreen.module.css";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui";
import { FinancesTab } from "./FinancesTab";
import { IntelTab } from "./IntelTab";
import styles from "./Reports.module.css";
import { StatsTab } from "./StatsTab";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

const LABELS: Record<ReportTab, string> = {
  intel: "Intel",
  stats: "Stats",
  finances: "Finances",
};

function isReportTab(value: string | undefined): value is ReportTab {
  return REPORT_TABS.includes(value as ReportTab);
}

export function ReportsScreen() {
  const { tab } = useParams();
  const navigate = useNavigate();
  if (tab !== undefined && !isReportTab(tab)) {
    return <Navigate to={PATHS.reports} replace />;
  }
  const current: ReportTab = tab ?? "intel";

  return (
    <div className={settings.screen}>
      <header className={settings.header}>
        <Link to={PATHS.command} className={settings.back}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path d="M15 6l-6 6 6 6" />
          </svg>
          Command view
        </Link>
        <span className={settings.divider} />
        <h1 className={settings.title}>Reports</h1>
      </header>
      <Tabs
        className={styles.tabs}
        value={current}
        onValueChange={(value) =>
          navigate(PATHS.reportTab(value as ReportTab), { replace: true })
        }
      >
        <TabsList aria-label="Reports" className={styles.tabList}>
          {REPORT_TABS.map((value) => (
            <TabsTrigger key={value} value={value}>
              {LABELS[value]}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value="intel" className={styles.content}>
          <IntelTab />
        </TabsContent>
        <TabsContent value="stats" className={styles.content}>
          <StatsTab />
        </TabsContent>
        <TabsContent value="finances" className={styles.content}>
          <FinancesTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
