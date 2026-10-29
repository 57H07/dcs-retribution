// Minimal app bar of the web shell (WEB-00.3): every action of the Qt menus,
// toolbars and top panel stays reachable. The full top bar is WEB-01.1.
import { commandErrorMessage } from "../api/commands";
import { usePassTurnMutation } from "../api/liberationApi";
import { Button, Menu, MenuEntry, useToast } from "../ui";
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
        { label: "Preferences", onSelect: () => qt.openDialog("preferences") },
        "separator",
        { label: "Exit", onSelect: () => qt.openDialog("quit") },
      ],
    },
    {
      label: "Campaign",
      items: [
        { label: "Air Wing", onSelect: () => navigate(PATHS.airWing) },
        { label: "Transfers", onSelect: () => qt.openDialog("transfers") },
        {
          label: "Packages",
          onSelect: () => qt.openDialog("air-tasking-order"),
        },
        { label: "New package", shortcut: "N", onSelect: onNewPackage },
        "separator",
        { label: "Settings", onSelect: () => navigate(PATHS.settings) },
        { label: "Stats", onSelect: () => qt.openDialog("stats") },
        { label: "Notes", onSelect: () => qt.openDialog("notes") },
        { label: "Reports", onSelect: () => navigate(PATHS.reports) },
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
  const toast = useToast();
  const [passTurn, { isLoading: passingTurn }] = usePassTurnMutation();

  const onPassTurn = async () => {
    const result = await passTurn();
    if ("error" in result) {
      toast({
        title: "Could not pass the turn",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    }
  };

  return (
    <header className={styles.bar}>
      <NavLink to={PATHS.command} className={styles.brand} end>
        Retribution
      </NavLink>
      <nav className={styles.menus} aria-label="Main menu">
        {appMenus({ qt, navigate, onNewPackage, onShowHelp }).map((menu) => (
          <Menu key={menu.label} label={menu.label} items={menu.items} />
        ))}
      </nav>
      <div className={styles.quick}>
        <Button variant="ghost" onClick={() => navigate(PATHS.airWing)}>
          Air Wing
        </Button>
        <Button variant="ghost" onClick={() => qt.openDialog("transfers")}>
          Transfers
        </Button>
        <Button
          variant="ghost"
          onClick={() => qt.openDialog("air-tasking-order")}
        >
          Packages
        </Button>
      </div>
      <div className={styles.turn}>
        <Button onClick={onPassTurn} disabled={passingTurn}>
          Pass turn
        </Button>
        <Button variant="primary" onClick={() => qt.openDialog("take-off")}>
          Take off
        </Button>
      </div>
    </header>
  );
}
