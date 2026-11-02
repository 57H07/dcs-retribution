// Must come before leaflet: lets Leaflet draw the links and bases.
import "../testutils/leafletSvg";
import { CampaignPreview } from "../api/liberationApi";
import { CampaignMapPreview } from "./CampaignMapPreview";
import { render, screen } from "@testing-library/react";

const basemap = vi.fn();
vi.mock("react-esri-leaflet", () => ({
  BasemapLayer: (props: unknown) => {
    basemap(props);
    return null;
  },
}));

const PREVIEW: CampaignPreview = {
  south_west: { lat: 32, lng: 35 },
  north_east: { lat: 33, lng: 36 },
  bases: [
    {
      name: "Ramat David",
      position: { lat: 32, lng: 35 },
      side: "blue",
      kind: "AIRBASE",
    },
    {
      name: "Damascus",
      position: { lat: 33, lng: 36 },
      side: "red",
      kind: "AIRBASE",
    },
  ],
  links: [{ from_index: 0, to_index: 1, front_line: true }],
  blue_bases: 1,
  red_bases: 1,
  front_lines: 1,
};

function setOnline(online: boolean) {
  vi.spyOn(window.navigator, "onLine", "get").mockReturnValue(online);
}

afterEach(() => {
  vi.restoreAllMocks();
  basemap.mockClear();
});

describe("CampaignMapPreview", () => {
  it("shows the campaign on the online basemap, with its bases named", () => {
    setOnline(true);
    render(<CampaignMapPreview preview={PREVIEW} />);
    expect(
      screen.getByRole("img", {
        name: "Campaign map preview: 1 friendly bases, 1 enemy bases, 1 front lines",
      }),
    ).toBeInTheDocument();
    expect(basemap).toHaveBeenCalled();
    expect(screen.getByText("Ramat David")).toBeInTheDocument();
    expect(screen.getByText("Damascus")).toBeInTheDocument();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("keeps the bases and says there is no terrain offline", () => {
    setOnline(false);
    render(<CampaignMapPreview preview={PREVIEW} />);
    expect(basemap).not.toHaveBeenCalled();
    expect(screen.getByRole("status")).toHaveTextContent("Offline");
    expect(screen.getByText("Damascus")).toBeInTheDocument();
  });

  it("copes with a campaign without a base on the map", () => {
    setOnline(true);
    render(
      <CampaignMapPreview
        preview={{
          ...PREVIEW,
          south_west: undefined,
          north_east: undefined,
          bases: [],
          links: [],
        }}
      />,
    );
    expect(screen.getByRole("img")).toBeInTheDocument();
  });
});
