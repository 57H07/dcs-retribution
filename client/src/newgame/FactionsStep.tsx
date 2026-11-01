// Step 2: both factions, recommended by the campaign; their units can be changed
// and saved as a new faction. The changes stay here until the campaign is generated.
import { FactionUnits } from "../airwingconfig/FactionUnits";
import { useCommand } from "../airwing/useCommand";
import {
  NewGameOptions,
  useGetNewGameFactionQuery,
  useSaveNewGameFactionMutation,
} from "../api/liberationApi";
import { Button, Modal, ModalClose } from "../ui";
import styles from "./NewGame.module.css";
import { RichText } from "./RichText";
import {
  FactionDraft,
  WizardState,
  addUnit,
  factionChoice,
  factionDraft,
  toggleUnit,
} from "./wizardState";
import { useState } from "react";

function SaveFaction({ draft }: { draft: FactionDraft }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [authors, setAuthors] = useState("");
  const [save] = useSaveNewGameFactionMutation();
  const run = useCommand();
  return (
    <Modal
      open={open}
      onOpenChange={setOpen}
      title="Save as new faction"
      trigger={<Button>Save as new faction</Button>}
      footer={
        <>
          <ModalClose asChild>
            <Button>Cancel</Button>
          </ModalClose>
          <Button
            variant="primary"
            onClick={async () => {
              const saved = await run(
                save({
                  saveFactionJs: {
                    faction: factionChoice(draft),
                    name,
                    description,
                    authors,
                  },
                }),
                "Faction not saved",
              );
              if (saved) {
                setOpen(false);
              }
            }}
          >
            Save
          </Button>
        </>
      }
    >
      <div className={styles.form}>
        {(
          [
            ["Name", name, setName],
            ["Description", description, setDescription],
            ["Author(s)", authors, setAuthors],
          ] as const
        ).map(([label, value, set]) => (
          <label key={label} className={styles.field}>
            <span className={styles.label}>{label}</span>
            <input
              className={styles.input}
              value={value}
              onChange={(event) => set(event.target.value)}
            />
          </label>
        ))}
      </div>
    </Modal>
  );
}

function FactionColumn({
  title,
  factions,
  draft,
  recommended,
  onChange,
}: {
  title: string;
  factions: string[];
  draft: FactionDraft;
  recommended: boolean;
  onChange: (draft: FactionDraft) => void;
}) {
  const { currentData: sheet } = useGetNewGameFactionQuery({
    name: draft.name,
  });
  return (
    <section className={styles.factionColumn} aria-label={title}>
      <label className={styles.field}>
        <span className={styles.label}>{title}</span>
        <select
          className={styles.select}
          value={draft.name}
          onChange={(event) => onChange(factionDraft(event.target.value))}
        >
          {factions.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
      {recommended && (
        <p className={styles.hint}>Recommended by this campaign.</p>
      )}
      {!sheet ? (
        <p className={styles.hint}>Loading the faction…</p>
      ) : (
        <>
          <div className={styles.factionText}>
            <RichText html={sheet.description} />
            {Object.keys(sheet.requirements).length > 0 && (
              <>
                <strong>Requirements</strong>
                <ul>
                  {Object.entries(sheet.requirements).map(([key, value]) => (
                    <li key={key}>
                      {key}: {value}
                    </li>
                  ))}
                </ul>
              </>
            )}
            <p className={styles.hint}>By {sheet.authors}</p>
          </div>
          <SaveFaction draft={draft} />
          <FactionUnits
            sheet={sheet}
            hasJtac={draft.hasJtac ?? sheet.has_jtac}
            doctrine={draft.doctrine ?? sheet.doctrine}
            added={draft.added}
            removed={draft.removed}
            onToggleUnit={(group, unit) =>
              onChange(toggleUnit(draft, group, unit))
            }
            onAddUnit={(group, unit) => onChange(addUnit(draft, group, unit))}
            onJtacChange={(hasJtac) => onChange({ ...draft, hasJtac })}
            onDoctrineChange={(doctrine) => onChange({ ...draft, doctrine })}
          />
        </>
      )}
    </section>
  );
}

export function FactionsStep({
  options,
  state,
  onChange,
}: {
  options: NewGameOptions;
  state: WizardState;
  onChange: (state: WizardState) => void;
}) {
  const campaign = options.campaigns.find((c) => c.id === state.campaignId);
  // Inverting the map swaps the recommendations.
  const [blueWanted, redWanted] = state.inverted
    ? [campaign?.recommended_red_faction, campaign?.recommended_blue_faction]
    : [campaign?.recommended_blue_faction, campaign?.recommended_red_faction];
  return (
    <div className={styles.factions}>
      <FactionColumn
        title="Player faction"
        factions={options.factions}
        draft={state.blue}
        recommended={state.blue.name === blueWanted}
        onChange={(blue) => onChange({ ...state, blue })}
      />
      <FactionColumn
        title="Enemy faction"
        factions={options.factions}
        draft={state.red}
        recommended={state.red.name === redWanted}
        onChange={(red) => onChange({ ...state, red })}
      />
    </div>
  );
}
