import { Tgo as TgoModel } from "../../api/liberationApi";
import { useIsInspectedTgo } from "../../maplayers/mapSelection";
import { useSymbolIcon } from "../../maplayers/zoom";
import SplitLines from "../splitlines/SplitLines";
import { Tooltip } from "react-leaflet";

// Symbol of a TGO, sized for the current map zoom.
export function useTgoIcon(tgo: TgoModel) {
  return useSymbolIcon(tgo.sidc, "tgo");
}

export function TgoTooltip(props: { tgo: TgoModel }) {
  // The inspector card shows the same site, under a mouse left on the marker.
  const inspected = useIsInspectedTgo(props.tgo.id);
  if (inspected) {
    return null;
  }
  return (
    <Tooltip>
      {`${props.tgo.name} (${props.tgo.control_point_name})`}
      <br />
      <SplitLines items={props.tgo.units} />
    </Tooltip>
  );
}
