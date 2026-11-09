import type {
  CampaignObjective,
  CampaignObjectives,
} from "../../api/liberationApi";
import { recordFetch, restoreFetch } from "../../shell/testing";
import { renderWithProviders } from "../../testutils";
import ObjectivesLayer from "./ObjectivesLayer";
import { screen, waitFor } from "@testing-library/react";
import { PropsWithChildren } from "react";

const mockCircleMarker = vi.fn();
vi.mock("react-leaflet", () => ({
  LayerGroup: (props: PropsWithChildren<any>) => <>{props.children}</>,
  CircleMarker: (props: PropsWithChildren<any>) => {
    mockCircleMarker(props);
    return <div data-testid="marker">{props.children}</div>;
  },
  Tooltip: (props: PropsWithChildren<any>) => <>{props.children}</>,
}));

afterEach(() => {
  restoreFetch();
  mockCircleMarker.mockClear();
});

function objective(
  overrides: Partial<CampaignObjective> = {},
): CampaignObjective {
  return {
    title: "Capture Golan North",
    kind: "capture",
    target: "Golan North",
    state: "In progress",
    reward: "",
    expected: "",
    granted: "",
    targets: [
      {
        id: "golan",
        name: "Golan North",
        position: { lat: 33.1, lng: 35.8 },
        remaining: true,
      },
    ],
    ...overrides,
  };
}

describe("ObjectivesLayer", () => {
  it("marks what is left of each objective in progress", async () => {
    const data: CampaignObjectives = {
      turn: 2,
      objectives: [
        objective(),
        objective({
          title: "Blind the air defences",
          kind: "destroy",
          targets: [
            {
              id: "golan",
              name: "Golan North",
              position: { lat: 33.1, lng: 35.8 },
              remaining: true,
            },
            {
              id: "sa6",
              name: "SA-6",
              position: { lat: 33, lng: 36 },
              remaining: false,
            },
          ],
        }),
        objective({ title: "Hold Batumi", state: "Missed" }),
      ],
    };
    recordFetch(204, undefined, { "/objectives": data });
    renderWithProviders(<ObjectivesLayer />);

    // One marker per target still standing, with every objective about it.
    await waitFor(() =>
      expect(screen.getAllByTestId("marker")).toHaveLength(1),
    );
    const [marker] = screen.getAllByTestId("marker");
    expect(marker).toHaveTextContent("Golan North");
    expect(marker).toHaveTextContent("Capture Golan North");
    expect(marker).toHaveTextContent("Blind the air defences");
    expect(marker).not.toHaveTextContent("Hold Batumi");
    expect(mockCircleMarker.mock.lastCall?.[0].center).toEqual({
      lat: 33.1,
      lng: 35.8,
    });
  });
});
