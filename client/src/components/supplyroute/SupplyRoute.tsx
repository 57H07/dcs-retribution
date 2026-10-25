import { SupplyRoute as SupplyRouteModel } from "../../api/liberationApi";
import {
  LAYER_COLORS,
  SUPPLY_ROUTE_ACTIVE_WEIGHT,
  SUPPLY_ROUTE_WEIGHT,
} from "../../maplayers/colors";
import SplitLines from "../splitlines/SplitLines";
import { Polyline as LPolyline } from "leaflet";
import { useEffect, useRef } from "react";
import { Polyline, Tooltip } from "react-leaflet";

interface SupplyRouteProps {
  route: SupplyRouteModel;
}

function SupplyRouteTooltip(props: SupplyRouteProps) {
  if (!props.route.active_transports.length) {
    return <Tooltip>This supply route is inactive.</Tooltip>;
  }

  return (
    <Tooltip>
      <SplitLines items={props.route.active_transports} />
    </Tooltip>
  );
}

function ActiveSupplyRouteHighlight(props: SupplyRouteProps) {
  if (!props.route.active_transports.length) {
    return <></>;
  }

  return (
    <Polyline positions={props.route.points} color={LAYER_COLORS.supplyRouteActiveTransport}
      weight={SUPPLY_ROUTE_ACTIVE_WEIGHT} />
  );
}

function colorFor(route: SupplyRouteModel) {
  if (route.front_active) {
    return LAYER_COLORS.supplyRouteFrontActive;
  }
  if (route.blue) {
    return LAYER_COLORS.supplyRouteBlue;
  }
  return LAYER_COLORS.supplyRouteRed;
}

export default function SupplyRoute(props: SupplyRouteProps) {
  const color = colorFor(props.route);
  const weight = props.route.is_sea
    ? SUPPLY_ROUTE_WEIGHT.sea
    : SUPPLY_ROUTE_WEIGHT.land;

  const path = useRef<LPolyline | null>();

  useEffect(() => {
    // Ensure that the highlight line draws on top of this. We have to bring
    // this to the back rather than bringing the highlight to the front because
    // the highlight won't necessarily be drawn yet.
    path.current?.bringToBack();
  });

  return (
    <Polyline
      positions={props.route.points}
      pathOptions={{ color: color, weight: weight}}
      ref={(ref) => (path.current = ref)}
    >
      <SupplyRouteTooltip {...props} />
      <ActiveSupplyRouteHighlight {...props} />
    </Polyline>
  );
}
