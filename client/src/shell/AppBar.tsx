// Top bar of the command view (WEB-01.1, after the WEB-00.3 app bar): the
// campaign state of QTopPanel, the campaign screens and every action of the Qt
// menus and toolbars. The turn buttons sit at the bottom right of the map.
import { CampaignStatus } from "../command/CampaignStatus";
import { Button, IconButton, Menu, MenuEntry } from "../ui";
import styles from "./AppBar.module.css";
import { PATHS } from "./paths";
import { QtCommands, useQtCommands } from "./useQtCommands";
import { NavLink, useNavigate } from "react-router-dom";

export interface AppBarProps {
  onNewPackage: () => void;
  onShowHelp: () => void;
}

interface MenuContext {
  qt: QtCommands;
  navigate: (path: string) => void;
  onNewPackage: () => void;
  onShowHelp: () => void;
}

/** The app bar menus, as data so that tests can check nothing is missing. */
export function appMenus({
  qt,
  navigate,
  onNewPackage,
  onShowHelp,
}: MenuContext): { label: string; items: MenuEntry[] }[] {
  return [
    {
      label: "File",
      items: [
        { label: "New game", onSelect: () => navigate(PATHS.newGame) },
        { label: "Open…", onSelect: () => qt.openDialog("open-game") },
        "separator",
        {
          label: "Save",
          shortcut: "Ctrl+S",
          onSelect: () => qt.openDialog("save-game"),
        },
        { label: "Save as…", onSelect: () => qt.openDialog("save-game-as") },
        "separator",
        { label: "Preferences", onSelect: () => navigate(PATHS.preferences) },
        "separator",
        { label: "Exit", onSelect: () => qt.openDialog("quit") },
      ],
    },
    {
      label: "Campaign",
      items: [
        { label: "Air Wing", onSelect: () => navigate(PATHS.airWing) },
        { label: "Transfers", onSelect: () => qt.openDialog("transfers") },
        { label: "New package", shortcut: "N", onSelect: onNewPackage },
        "separator",
        { label: "Settings", onSelect: () => navigate(PATHS.settings) },
        { label: "Stats", onSelect: () => navigate(PATHS.reportTab("stats")) },
        { label: "Notes", onSelect: () => qt.openDialog("notes") },
        { label: "Reports", onSelect: () => navigate(PATHS.reports) },
        { label: "Info panel", onSelect: () => qt.openDialog("info-panel") },
        { label: "Last debriefing", onSelect: () => navigate(PATHS.debrief) },
      ],
    },
    {
      label: "Tools",
      items: [
        {
          label: "Generate a Pretense campaign",
          onSelect: () => qt.openDialog("pretense-campaign"),
        },
        {
          label: "Import layouts",
          onSelect: () => qt.openDialog("import-layouts"),
        },
      ],
    },
    {
      label: "Help",
      items: [
        { label: "Keyboard shortcuts", shortcut: "?", onSelect: onShowHelp },
        { label: "Online manual", onSelect: () => qt.openLink("manual") },
        { label: "Releases", onSelect: () => qt.openLink("releases") },
        {
          label: "ED forum thread",
          onSelect: () => qt.openLink("forum-thread"),
        },
        { label: "Report an issue", onSelect: () => qt.openLink("issues") },
        { label: "Show logs", onSelect: () => qt.openDialog("logs") },
        "separator",
        { label: "Discord server", onSelect: () => qt.openLink("discord") },
        { label: "GitHub repository", onSelect: () => qt.openLink("github") },
        { label: "Ukraine", onSelect: () => qt.openLink("ukraine") },
        {
          label: "DCS: Pretense Discord",
          onSelect: () => qt.openLink("pretense-discord"),
        },
        "separator",
        {
          label: "About DCS Retribution",
          onSelect: () => qt.openDialog("about"),
        },
      ],
    },
  ];
}

export function AppBar({ onNewPackage, onShowHelp }: AppBarProps) {
  const qt = useQtCommands();
  const navigate = useNavigate();

  return (
    <header className={styles.bar}>
      <NavLink to={PATHS.command} className={styles.brand} end>
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
        >
          <path d="M12 2l9 5v10l-9 5-9-5V7z" />
          <path d="M12 7l4 2.5v5L12 17l-4-2.5v-5z" />
        </svg>
        Retribution
      </NavLink>
      <nav className={styles.menus} aria-label="Main menu">
        {appMenus({ qt, navigate, onNewPackage, onShowHelp }).map((menu) => (
          <Menu key={menu.label} label={menu.label} items={menu.items} />
        ))}
      </nav>
      <CampaignStatus
        onOpenFinances={() => navigate(PATHS.reportTab("finances"))}
        onOpenIntel={() => navigate(PATHS.reportTab("intel"))}
      />
      <nav className={styles.screens} aria-label="Campaign screens">
        <Button variant="ghost" onClick={() => navigate(PATHS.airWing)}>
          Air Wing
        </Button>
        <Button variant="ghost" onClick={() => qt.openDialog("transfers")}>
          Transfers
        </Button>
        <Button variant="ghost" onClick={() => navigate(PATHS.reports)}>
          Reports
        </Button>
        <IconButton
          aria-label="Settings"
          onClick={() => navigate(PATHS.settings)}
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z" />
          </svg>
        </IconButton>
      </nav>
    </header>
  );
}
