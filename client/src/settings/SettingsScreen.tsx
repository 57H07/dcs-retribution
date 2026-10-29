// Settings screen (WEB-07.1), generated from GET /settings/: pages, sections,
// controls by kind, help, "Modified" markers, search and reset per page. The
// engine owns every rule (bounds, side effects): this only shows and sends.
import { commandErrorMessage } from "../api/commands";
import {
  Setting,
  SettingsPage,
  useGetSettingsQuery,
  useResetSettingsPageMutation,
  useSetSettingMutation,
} from "../api/liberationApi";
import { PATHS } from "../shell/paths";
import {
  Button,
  IconButton,
  Modal,
  ModalClose,
  Tooltip,
  useToast,
} from "../ui";
import { SettingControl, SettingValue } from "./SettingControl";
import styles from "./SettingsScreen.module.css";
import { modifiedCount, searchSettings } from "./search";
import { useEffect, useId, useMemo, useState } from "react";
import { Link } from "react-router-dom";

function SettingRow({ setting }: { setting: Setting }) {
  const [setSetting] = useSetSettingMutation();
  const toast = useToast();
  const [pending, setPending] = useState<SettingValue | undefined>(undefined);
  // The server answered (new schema): show its value.
  useEffect(() => setPending(undefined), [setting.value]);

  const change = async (value: SettingValue) => {
    setPending(value);
    const result = await setSetting({
      key: setting.key,
      settingValueUpdateJs: { value },
    });
    if ("error" in result) {
      setPending(undefined);
      toast({
        title: "Setting not changed",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    }
  };

  return (
    <div className={styles.row} data-testid={`setting-${setting.key}`}>
      <div className={styles.text}>
        <span className={styles.label}>
          {setting.label}
          {setting.tooltip && (
            <Tooltip content={setting.tooltip}>
              <IconButton
                aria-label={`About ${setting.label}`}
                className={styles.info}
              >
                ?
              </IconButton>
            </Tooltip>
          )}
        </span>
        {setting.detail && (
          <span className={styles.help}>{setting.detail}</span>
        )}
      </div>
      {setting.modified && (
        <span className={styles.modified} title="Differs from the default">
          Modified
        </span>
      )}
      <SettingControl
        setting={setting}
        value={pending ?? setting.value}
        onChange={change}
      />
    </div>
  );
}

function Section({
  title,
  description,
  settings,
}: {
  title: string;
  description?: string;
  settings: Setting[];
}) {
  const headingId = useId();
  return (
    <section className={styles.section} aria-labelledby={headingId}>
      <h2 id={headingId} className={styles.sectionTitle}>
        {title}
      </h2>
      {description && <p className={styles.sectionHelp}>{description}</p>}
      <div className={styles.rows}>
        {settings.map((setting) => (
          <SettingRow key={setting.key} setting={setting} />
        ))}
      </div>
    </section>
  );
}

function ResetPage({ page }: { page: SettingsPage }) {
  const [resetPage, { isLoading }] = useResetSettingsPageMutation();
  const [open, setOpen] = useState(false);
  const toast = useToast();
  const count = modifiedCount(page);

  const reset = async () => {
    const result = await resetPage({ pageId: page.id });
    setOpen(false);
    if ("error" in result) {
      toast({
        title: "Page not reset",
        description: commandErrorMessage(result.error),
        tone: "danger",
      });
    }
  };

  return (
    <Modal
      open={open}
      onOpenChange={setOpen}
      title={`Reset ${page.name}?`}
      description={`${count} setting${count === 1 ? "" : "s"} of this page will go back to ${count === 1 ? "its" : "their"} default value.`}
      trigger={<Button disabled={count === 0}>Reset page</Button>}
      footer={
        <>
          <ModalClose asChild>
            <Button>Cancel</Button>
          </ModalClose>
          <Button variant="danger" onClick={reset} disabled={isLoading}>
            Reset
          </Button>
        </>
      }
    />
  );
}

function SearchResults({
  pages,
  query,
}: {
  pages: SettingsPage[];
  query: string;
}) {
  const matches = searchSettings(pages, query);
  if (matches.length === 0) {
    return <p className={styles.state}>No setting matches “{query}”.</p>;
  }
  // Group consecutive matches by page and section, as on the pages.
  const groups: { title: string; settings: Setting[] }[] = [];
  for (const match of matches) {
    const title = `${match.page.name} › ${match.section}`;
    const last = groups[groups.length - 1];
    if (last?.title === title) {
      last.settings.push(match.setting);
    } else {
      groups.push({ title, settings: [match.setting] });
    }
  }
  return (
    <>
      {groups.map((group) => (
        <Section
          key={group.title}
          title={group.title}
          settings={group.settings}
        />
      ))}
    </>
  );
}

export function SettingsScreen() {
  const { data, error, isLoading } = useGetSettingsQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  const [pageId, setPageId] = useState<string | undefined>(undefined);
  const [query, setQuery] = useState("");
  const pages = useMemo(() => data?.pages ?? [], [data]);
  const page = pages.find((p) => p.id === pageId) ?? pages[0];
  const searching = query.trim() !== "";

  let body;
  if (isLoading) {
    body = <p className={styles.state}>Loading settings…</p>;
  } else if (error) {
    body = (
      <p className={styles.state} role="alert">
        {commandErrorMessage(error)}
      </p>
    );
  } else if (!page) {
    body = <p className={styles.state}>No settings to show.</p>;
  } else if (searching) {
    body = <SearchResults pages={pages} query={query.trim()} />;
  } else {
    body = page.sections.map((section) => (
      <Section
        key={section.name}
        title={section.name}
        description={section.description}
        settings={section.settings}
      />
    ));
  }

  const count = page ? modifiedCount(page) : 0;

  return (
    <div className={styles.screen}>
      <header className={styles.header}>
        <Link to={PATHS.command} className={styles.back}>
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
        <span className={styles.divider} />
        <h1 className={styles.title}>Settings</h1>
        <label className={styles.search}>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="M20 20l-3.5-3.5" />
          </svg>
          <input
            type="search"
            placeholder="Search all settings"
            aria-label="Search all settings"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <span className={styles.spacer} />
        {page && !searching && (
          <>
            <span className={styles.changes}>
              {count} change{count === 1 ? "" : "s"} from defaults
            </span>
            <ResetPage page={page} />
          </>
        )}
      </header>
      <div className={styles.columns}>
        <nav aria-label="Settings pages" className={styles.nav}>
          {pages.map((p) => {
            const current = !searching && p.id === page?.id;
            const changed = modifiedCount(p);
            return (
              <button
                key={p.id}
                type="button"
                className={styles.navItem}
                aria-current={current ? "page" : undefined}
                onClick={() => {
                  setPageId(p.id);
                  setQuery("");
                }}
              >
                <span>{p.name}</span>
                {changed > 0 && (
                  <span
                    className={styles.navCount}
                    aria-label={`${changed} modified`}
                  >
                    {changed}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
        <div className={styles.main}>{body}</div>
      </div>
    </div>
  );
}
