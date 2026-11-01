// About DCS Retribution (WEB-08.2): version and credits from GET /about. The
// repository opens in the system browser through the native bridge.
import { useGetAboutQuery } from "../api/liberationApi";
import { useNativeCommands } from "../shell/useNativeCommands";
import { Button } from "../ui";
import { QueryBody, ScreenFrame } from "./ScreenFrame";
import styles from "./Secondary.module.css";

export function AboutScreen() {
  const query = useGetAboutQuery();
  const native = useNativeCommands();
  return (
    <ScreenFrame
      title="About"
      actions={
        <Button variant="ghost" onClick={() => native.openLink("github")}>
          Source code
        </Button>
      }
    >
      <QueryBody query={query} name="credits">
        {(about) => (
          <>
            <section className={styles.section} aria-label="Version">
              <h2 className={styles.sectionTitle}>
                DCS Retribution{" "}
                <span className={styles.count}>{about.version}</span>
              </h2>
              <p className={styles.prose}>{about.authors}</p>
            </section>
            <section className={styles.section} aria-label="Contributors">
              <h2 className={styles.sectionTitle}>Contributors</h2>
              <p className={styles.prose}>{about.contributors.join(", ")}</p>
            </section>
            <section className={styles.section} aria-label="Special thanks">
              <h2 className={styles.sectionTitle}>Special thanks</h2>
              <ul className={styles.list}>
                {about.special_thanks.map((thanks) => (
                  <li key={thanks.name}>
                    <strong>{thanks.name}</strong> {thanks.reason}
                  </li>
                ))}
              </ul>
            </section>
            <section className={styles.section} aria-label="Attributions">
              <h2 className={styles.sectionTitle}>Attributions</h2>
              <ul className={styles.list}>
                {about.attributions.map((attribution) => (
                  <li key={attribution.url}>
                    {attribution.text}{" "}
                    <span className={`${styles.cardDetail} ${styles.link}`}>
                      {attribution.url}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </QueryBody>
    </ScreenFrame>
  );
}
