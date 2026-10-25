import {
  FrontLine as FrontLineModel,
  useOpenNewFrontLinePackageDialogMutation,
} from "../../api/liberationApi";
import { FRONT_LINE_WEIGHT, LAYER_COLORS } from "../../maplayers/colors";
import { Polyline } from "react-leaflet";

interface FrontLineProps {
  front: FrontLineModel;
}

function FrontLine(props: FrontLineProps) {
  const [openNewPackageDialog] = useOpenNewFrontLinePackageDialogMutation();
  return (
    <Polyline
      positions={props.front.extents}
      weight={FRONT_LINE_WEIGHT}
      color={LAYER_COLORS.frontLine}
      eventHandlers={{
        contextmenu: () => {
          openNewPackageDialog({ frontLineId: props.front.id });
        },
      }}
    />
  );
}

export default FrontLine;
