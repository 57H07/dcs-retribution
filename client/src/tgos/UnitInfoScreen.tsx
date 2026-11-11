// Unit info sheet (WEB-08.3), the web version of the Qt QUnitInfoWindow: banner,
// origin, role, tasks of an aircraft, and description of a unit type. Open it from
// anywhere with PATHS.unit(kind, name), name being the unit type's variant id.
import { HTTP_URL } from "../api/backend";
import { UnitInfo, useGetUnitInfoQuery } from "../api/liberationApi";
import { QueryBody, ScreenFrame } from "../secondary/ScreenFrame";
import secondary from "../secondary/Secondary.module.css";
import { UnitKind } from "../shell/paths";
import { Button } from "../ui";
import styles from "./TgoScreen.module.css";
import { useNavigate, useParams } from "react-router-dom";

export function unitBannerUrl(kind: UnitKind, name: string): string {
  const query = new URLSearchParams({ kind, name });
  return `${HTTP_URL}unit-info/banner?${query}`;
}

export function UnitInfoScreen() {
  const { kind = "", name = "" } = useParams();
  const navigate = useNavigate();
  const query = useGetUnitInfoQuery({ kind: kind as UnitKind, name });
  return (
    <ScreenFrame
      title={query.data?.display_name ?? "Unit info"}
      actions={
        <Button variant="ghost" onClick={() => navigate(-1)}>
          Back
        </Button>
      }
    >
      <QueryBody query={query} name="unit details">
        {(info) => <UnitInfoBody info={info} />}
      </QueryBody>
    </ScreenFrame>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className={secondary.help}>{label}</dt>
      <dd className={styles.factValue}>{value}</dd>
    </>
  );
}

function UnitInfoBody({ info }: { info: UnitInfo }) {
  return (
    <>
      <img
        className={styles.banner}
        src={unitBannerUrl(info.kind, info.name)}
        alt={info.display_name}
      />
      <dl className={styles.facts}>
        <Fact
          label="Name"
          value={`${info.manufacturer} ${info.display_name}`}
        />
        <Fact label="Country of origin" value={info.country_of_origin} />
        <Fact label="Role" value={info.role} />
        <Fact label="Variant introduction" value={info.year_introduced} />
        {info.purpose !== "" && (
          <Fact label="In the campaign" value={info.purpose} />
        )}
        {info.tasks.length > 0 && (
          <Fact label="In-game tasks" value={info.tasks.join(", ")} />
        )}
      </dl>
      <p className={styles.description}>{info.description}</p>
    </>
  );
}
