// The targets of the campaign objectives in progress (#194): one dashed ring per
// base or ground object still to take, destroy or keep, with every objective
// about it on hover.
import { useGetObjectivesQuery } from "../../api/liberationApi";
import type { ObjectiveTarget } from "../../api/liberationApi";
import { LAYER_COLORS } from "../../maplayers/colors";
import { CircleMarker, LayerGroup, Tooltip } from "react-leaflet";

const RING = {
  color: LAYER_COLORS.objective,
  weight: 2,
  dashArray: "6 4",
  fill: false,
};

interface Marked {
  target: ObjectiveTarget;
  titles: string[];
}

export default function ObjectivesLayer() {
  const { data } = useGetObjectivesQuery();
  const marked = new Map<string, Marked>();
  for (const objective of data?.objectives ?? []) {
    if (objective.state !== "In progress") {
      continue;
    }
    for (const target of objective.targets) {
      if (!target.remaining) {
        continue;
      }
      const entry = marked.get(target.id) ?? { target, titles: [] };
      entry.titles.push(objective.title);
      marked.set(target.id, entry);
    }
  }
  return (
    <LayerGroup>
      {[...marked.values()].map(({ target, titles }) => (
        <CircleMarker
          key={target.id}
          center={target.position}
          radius={18}
          pathOptions={RING}
        >
          <Tooltip>
            <strong>{target.name}</strong>
            {titles.map((title) => (
              <div key={title}>Objective: {title}</div>
            ))}
          </Tooltip>
        </CircleMarker>
      ))}
    </LayerGroup>
  );
}
