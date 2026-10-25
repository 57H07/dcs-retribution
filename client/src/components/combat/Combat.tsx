import CombatModel from "../../api/combat";
import { LAYER_COLORS } from "../../maplayers/colors";
import { LatLng } from "leaflet";
import { Polygon, Polyline } from "react-leaflet";

interface CombatProps {
  combat: CombatModel;
}

function CombatFootprint(props: CombatProps) {
  if (!props.combat.footprint) {
    return <></>;
  }

  return (
    <Polygon
      positions={props.combat.footprint}
      color={LAYER_COLORS.combat}
      interactive={false}
      fillOpacity={0.2}
    />
  );
}

function CombatLines(props: CombatProps) {
  if (!props.combat.flight_position || !props.combat.target_positions) {
    return <></>;
  }

  const flightPosition: LatLng = props.combat.flight_position;
  return (
    <>
      {props.combat.target_positions.map((position, idx) => {
        return (
          <Polyline
            key={idx}
            positions={[flightPosition, position]}
            color={LAYER_COLORS.combat}
            interactive={false}
          />
        );
      })}
    </>
  );
}

export default function Combat(props: CombatProps) {
  return (
    <>
      <CombatFootprint {...props} />
      <CombatLines {...props} />
    </>
  );
}
