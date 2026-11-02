// Step 1, after mockups/NewGameMap.dc.html: filterable campaign list, the campaign on
// the real map, and its description from the YAML.
import {
  NewGameCampaign,
  NewGameOptions,
  useGetCampaignPreviewQuery,
} from "../api/liberationApi";
import { commandErrorMessage } from "../api/commands";
import { CampaignMapPreview } from "./CampaignMapPreview";
import styles from "./NewGame.module.css";
import { RichText } from "./RichText";
import { CampaignFilter, filterCampaigns } from "./wizardState";
import { ReactNode, useMemo, useState } from "react";

function Chips({
  label,
  values,
  selected,
  onSelect,
}: {
  label: string;
  values: string[];
  selected: string | null;
  onSelect: (value: string | null) => void;
}) {
  return (
    <div className={styles.chips} role="group" aria-label={label}>
      {values.map((value) => (
        <button
          key={value}
          type="button"
          className={styles.chip}
          aria-pressed={value === selected}
          onClick={() => onSelect(value === selected ? null : value)}
        >
          {value}
        </button>
      ))}
    </div>
  );
}

export interface TheaterStepProps {
  options: NewGameOptions;
  selected?: NewGameCampaign;
  onSelect: (campaign: NewGameCampaign) => void;
  footer: ReactNode;
}

export function TheaterStep({
  options,
  selected,
  onSelect,
  footer,
}: TheaterStepProps) {
  const [filter, setFilter] = useState<CampaignFilter>({
    query: "",
    theater: null,
    era: null,
    showIncompatible: false,
  });
  const theaters = useMemo(
    () => [...new Set(options.campaigns.map((c) => c.theater))].sort(),
    [options.campaigns],
  );
  const eras = useMemo(
    () =>
      [
        ...new Set(
          options.campaigns.flatMap((c) => (c.era != null ? [c.era] : [])),
        ),
      ].sort(),
    [options.campaigns],
  );
  const shown = filterCampaigns(options.campaigns, filter);
  const preview = useGetCampaignPreviewQuery(
    { campaignId: selected?.id ?? "" },
    { skip: selected === undefined },
  );
  // The map stays up while the next campaign loads, and moves when it arrives.
  const map = preview.data;

  return (
    <div className={styles.theater}>
      <aside className={styles.aside}>
        <input
          className={styles.search}
          type="search"
          placeholder="Search campaigns"
          aria-label="Search campaigns"
          value={filter.query}
          onChange={(event) =>
            setFilter({ ...filter, query: event.target.value })
          }
        />
        <Chips
          label="Theater"
          values={theaters}
          selected={filter.theater}
          onSelect={(theater) => setFilter({ ...filter, theater })}
        />
        <Chips
          label="Era"
          values={eras}
          selected={filter.era}
          onSelect={(era) => setFilter({ ...filter, era })}
        />
        <label className={styles.check}>
          <input
            type="checkbox"
            checked={filter.showIncompatible}
            onChange={(event) =>
              setFilter({ ...filter, showIncompatible: event.target.checked })
            }
          />
          Show incompatible campaigns
        </label>
        <div className={styles.campaigns} aria-label="Campaigns" role="list">
          {shown.length === 0 && (
            <p className={styles.hint}>No campaign matches these filters.</p>
          )}
          {shown.map((campaign) => (
            <button
              key={campaign.id}
              type="button"
              role="listitem"
              className={styles.campaign}
              aria-current={campaign.id === selected?.id ? "true" : undefined}
              onClick={() => onSelect(campaign)}
            >
              <span className={styles.campaignName}>{campaign.name}</span>
              <span className={styles.hint}>
                {[campaign.theater, campaign.era, campaign.performance_label]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </button>
          ))}
        </div>
      </aside>
      <div className={styles.mapFrame}>
        {map && <CampaignMapPreview preview={map} />}
        {(preview.error || preview.isFetching || !map) && (
          <p className={styles.mapStatus} role="status">
            {preview.error
              ? commandErrorMessage(preview.error)
              : "Loading the map…"}
          </p>
        )}
      </div>
      <div className={styles.theaterDetails}>
        {selected && (
          <div className={styles.details}>
            <div className={styles.description}>
              <h2 className={styles.campaignTitle}>{selected.name}</h2>
              {selected.warning != null && (
                <p role="alert" className={styles.warning}>
                  {selected.warning}
                </p>
              )}
              <RichText html={selected.description} />
              <div className={styles.tags}>
                <span className={styles.blueTag}>
                  Blue · {selected.recommended_blue_faction}
                </span>
                <span className={styles.redTag}>
                  Red · {selected.recommended_red_faction}
                </span>
              </div>
              <p className={styles.hint}>By {selected.authors}</p>
            </div>
            <dl className={styles.facts}>
              <div>
                <dt>Bases</dt>
                <dd>{map ? `${map.blue_bases} : ${map.red_bases}` : "…"}</dd>
              </div>
              <div>
                <dt>Front lines</dt>
                <dd>{map ? map.front_lines : "…"}</dd>
              </div>
              <div>
                <dt>Start date</dt>
                <dd>{selected.start_date ?? "Free"}</dd>
              </div>
              <div title={selected.performance_text}>
                <dt>Performance</dt>
                <dd>{selected.performance_label}</dd>
              </div>
            </dl>
          </div>
        )}
      </div>
      <div className={styles.theaterFooter}>{footer}</div>
    </div>
  );
}
