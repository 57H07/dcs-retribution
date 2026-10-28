interface LocationTooltipTextProps {
  name: string;
  cutOff?: boolean;
}

export const LocationTooltipText = (props: LocationTooltipTextProps) => {
  return (
    <>
      <h3 style={{ margin: 0 }}>{props.name}</h3>
      {props.cutOff ? (
        <p style={{ margin: 0, color: "#d32f2f" }}>
          Cut off: no road, sea or air link. Only airdrops can resupply it.
        </p>
      ) : null}
    </>
  );
};

export default LocationTooltipText;
