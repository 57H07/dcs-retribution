import { ControlPoint } from "../../api/_liberationApi";
import { makeLocationMarkerEventHandlers } from "./EventHandlers";
import { useControlPointIcon } from "./Icons";
import LocationTooltipText from "./LocationTooltipText";
import { CircleMarker, Marker, Tooltip } from "react-leaflet";

interface StaticControlPointProps {
  controlPoint: ControlPoint;
}

export const StaticControlPoint = (props: StaticControlPointProps) => {
  const icon = useControlPointIcon(props.controlPoint);
  const cutOff = props.controlPoint.cut_off === true;
  return (
    <>
      {cutOff ? (
        // A base with no road, sea or air link to a friendly base (TRN-03).
        <CircleMarker
          center={props.controlPoint.position}
          radius={22}
          interactive={false}
          pathOptions={{
            color: "#d32f2f",
            weight: 3,
            dashArray: "6 4",
            fill: false,
          }}
        />
      ) : null}
      <Marker
        position={props.controlPoint.position}
        icon={icon}
        // We might draw other markers on top of the CP. The tooltips from the
        // other markers are helpful so we want to keep them, but make sure the CP
        // is always the clickable thing.
        zIndexOffset={1000}
        eventHandlers={makeLocationMarkerEventHandlers(props.controlPoint)}
      >
        <Tooltip>
          <LocationTooltipText name={props.controlPoint.name} cutOff={cutOff} />
        </Tooltip>
      </Marker>
    </>
  );
};
