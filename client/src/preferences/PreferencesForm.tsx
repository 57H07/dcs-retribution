// Install preferences form (WEB-07.2), shared by the Preferences screen and the
// first start. The server validates everything (folders, DCS installation): the
// form only edits, browses through the native bridge and shows its answers.
import { commandErrorMessage } from "../api/commands";
import {
  FolderPurpose,
  InstallPreferences,
  InstallPreferencesState,
  usePickFolderMutation,
  useSetInstallPreferencesMutation,
} from "../api/liberationApi";
import settings from "../settings/SettingsScreen.module.css";
import {
  Button,
  Modal,
  ModalClose,
  NumberField,
  Switch,
  useToast,
} from "../ui";
import styles from "./Preferences.module.css";
import { ReactNode, useEffect, useId, useState } from "react";

type FolderKey = "saved_game_dir" | "dcs_install_dir";

const FOLDERS: {
  key: FolderKey;
  purpose: FolderPurpose;
  label: string;
  help: string;
  problem: "saved_game_dir_problem" | "dcs_install_dir_problem";
}[] = [
  {
    key: "saved_game_dir",
    purpose: "saved-games",
    label: "DCS Saved Games folder",
    help: "Where DCS keeps missions, payloads and logs, e.g. Saved Games\\DCS.",
    problem: "saved_game_dir_problem",
  },
  {
    key: "dcs_install_dir",
    purpose: "dcs-install",
    label: "DCS installation folder",
    help: "Needed to replace Scripts/MissionScripting.lua.",
    problem: "dcs_install_dir_problem",
  },
];

function Row({
  label,
  help,
  problem,
  children,
}: {
  label: string;
  help?: ReactNode;
  problem?: string | null;
  children: ReactNode;
}) {
  return (
    <div className={settings.row}>
      <div className={settings.text}>
        <span className={settings.label}>{label}</span>
        {help && <span className={settings.help}>{help}</span>}
        {problem && (
          <span className={styles.problem} role="alert">
            {problem}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  const headingId = useId();
  return (
    <section className={settings.section} aria-labelledby={headingId}>
      <h2 id={headingId} className={settings.sectionTitle}>
        {title}
      </h2>
      <div className={settings.rows}>{children}</div>
    </section>
  );
}

export interface PreferencesFormProps {
  state: InstallPreferencesState;
  submitLabel: string;
  /** Text above the submit button (e.g. the first start warning). */
  children?: ReactNode;
  onSaved?: (state: InstallPreferencesState) => void;
}

export function PreferencesForm({
  state,
  submitLabel,
  children,
  onSaved,
}: PreferencesFormProps) {
  const [draft, setDraft] = useState<InstallPreferences>(state.preferences);
  const [confirmEmpty, setConfirmEmpty] = useState(false);
  const [save, { isLoading }] = useSetInstallPreferencesMutation();
  const [pickFolder] = usePickFolderMutation();
  const toast = useToast();
  // New server state (after a save or a reload): start again from it.
  useEffect(() => setDraft(state.preferences), [state.preferences]);

  const edit = (change: Partial<InstallPreferences>) =>
    setDraft((current) => ({ ...current, ...change }));

  const browse = async (key: FolderKey, purpose: FolderPurpose) => {
    const result = await pickFolder({
      folderPickRequestJs: { purpose, start: draft[key] },
    });
    if ("error" in result) {
      toast({
        title: "Could not open the folder dialog",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    } else if (result.data.path != null) {
      edit({ [key]: result.data.path });
    }
  };

  const submit = async (allowEmptyInstallDir: boolean) => {
    setConfirmEmpty(false);
    const result = await save({
      installPreferencesUpdateJs: {
        ...draft,
        allow_empty_install_dir: allowEmptyInstallDir,
      },
    });
    if ("error" in result) {
      toast({
        title: "Preferences not saved",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
      return;
    }
    if (result.data.warning != null) {
      toast({
        title: "MissionScripting.lua not replaced",
        description: result.data.warning,
        tone: "danger",
      });
    } else {
      toast({ title: "Preferences saved", tone: "success" });
    }
    onSaved?.(result.data);
  };

  const apply = () => {
    if (draft.dcs_install_dir.trim() === "") {
      setConfirmEmpty(true);
    } else {
      submit(false);
    }
  };

  const restartNote =
    draft.server_port !== state.preferences.server_port ||
    draft.web_ui !== state.preferences.web_ui;

  return (
    <form
      className={styles.form}
      onSubmit={(event) => {
        event.preventDefault();
        apply();
      }}
    >
      <Section title="DCS folders">
        {FOLDERS.map((folder) => (
          <Row
            key={folder.key}
            label={folder.label}
            help={folder.help}
            problem={
              draft[folder.key] === state.preferences[folder.key]
                ? state[folder.problem]
                : undefined
            }
          >
            <div className={styles.folder}>
              <input
                className={styles.path}
                aria-label={folder.label}
                value={draft[folder.key]}
                onChange={(event) => edit({ [folder.key]: event.target.value })}
              />
              <Button onClick={() => browse(folder.key, folder.purpose)}>
                Browse…
              </Button>
            </div>
          </Row>
        ))}
      </Section>
      <Section title="Options">
        <Row
          label="Prefer custom Liberation payloads"
          help="Use the payloads shipped with Retribution before the DCS ones."
        >
          <Switch
            aria-label="Prefer custom Liberation payloads"
            checked={draft.prefer_liberation_payloads}
            onCheckedChange={(checked) =>
              edit({ prefer_liberation_payloads: checked })
            }
          />
        </Row>
        <Row
          label="Setup preferences on every start"
          help="Show the first start setup at each launch."
        >
          <Switch
            aria-label="Setup preferences on every start"
            checked={draft.setup_preferences_on_every_start}
            onCheckedChange={(checked) =>
              edit({ setup_preferences_on_every_start: checked })
            }
          />
        </Row>
      </Section>
      <Section title="Advanced (restart required)">
        <Row label="Server port" help="Port of the local game server.">
          <NumberField
            label="Server port"
            hideLabel
            value={draft.server_port}
            min={1}
            max={65535}
            onValueChange={(value) => edit({ server_port: value })}
          />
        </Row>
        <Row
          label="Web interface, experimental"
          help="Fill the main window with the web interface."
        >
          <Switch
            aria-label="Web interface, experimental"
            checked={draft.web_ui}
            onCheckedChange={(checked) => edit({ web_ui: checked })}
          />
        </Row>
      </Section>
      {children}
      <div className={styles.actions}>
        {restartNote && (
          <span className={styles.note}>
            Restart Retribution to apply the port and web interface changes.
          </span>
        )}
        <Button type="submit" variant="primary" disabled={isLoading}>
          {submitLabel}
        </Button>
      </div>
      <Modal
        open={confirmEmpty}
        onOpenChange={setConfirmEmpty}
        title="Leave the DCS installation folder empty?"
        description="Without it, Retribution cannot replace Scripts/MissionScripting.lua and will not work properly until you replace that file yourself with resources/scripts/MissionScripting.lua. Only recommended for expert users."
        footer={
          <>
            <ModalClose asChild>
              <Button>Cancel</Button>
            </ModalClose>
            <Button variant="danger" onClick={() => submit(true)}>
              Leave it empty
            </Button>
          </>
        }
      />
    </form>
  );
}
