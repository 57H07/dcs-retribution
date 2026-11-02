import { FrontLine as FrontLineModel } from "../../api/liberationApi";
import {
  useInspect,
  useIsInspected,
  useNewPackage,
} from "../../maplayers/mapSelection";
import { FRONT_LINE_WEIGHT, LAYER_COLORS } from "../../maplayers/colors";
import { Polyline } from "react-leaflet";

interface FrontLineProps {
  front: FrontLineModel;
}

function FrontLine(props: FrontLineProps) {
  const newPackage = useNewPackage();
  const inspect = useInspect("frontLine");
  const inspected = useIsInspected("frontLine", props.front.id);
  return (
    <Polyline
      positions={props.front.extents}
      pathOptions={{
        weight: inspected ? FRONT_LINE_WEIGHT + 3 : FRONT_LINE_WEIGHT,
        color: LAYER_COLORS.frontLine,
      }}
      eventHandlers={{
        click: () => {
          inspect(props.front.id);
        },
        contextmenu: () => {
          newPackage("front-line", props.front.id);
        },
      }}
    />
  );
}

export default FrontLine;
