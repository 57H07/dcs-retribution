import { useRecenterOnGame } from "./useRecenterOnGame";
import { renderHook } from "@testing-library/react";
import { LatLngLiteral, Map } from "leaflet";

function fakeMap() {
  return { setView: vi.fn(), getZoom: () => 9 } as unknown as Map & {
    setView: ReturnType<typeof vi.fn>;
  };
}

function render(map: Map | null, center: LatLngLiteral) {
  return renderHook(
    (props: { map: Map | null; center: LatLngLiteral }) =>
      useRecenterOnGame(props.map, props.center),
    { initialProps: { map, center } },
  );
}

describe("useRecenterOnGame", () => {
  const center = { lat: 42, lng: 41 };

  it("centres the map once it exists, keeping its zoom", () => {
    const map = fakeMap();
    const { rerender } = render(null, center);
    rerender({ map, center });
    expect(map.setView).toHaveBeenCalledTimes(1);
    expect(map.setView.mock.calls[0].slice(0, 2)).toEqual([center, 9]);
  });

  it("stays where it is when the component renders again", () => {
    const map = fakeMap();
    const { rerender } = render(map, center);
    rerender({ map, center });
    rerender({ map, center });
    expect(map.setView).toHaveBeenCalledTimes(1);
  });

  it("recentres on a new center, even at the same place", () => {
    const map = fakeMap();
    const { rerender } = render(map, center);
    rerender({ map, center: { lat: 25, lng: 55 } });
    rerender({ map, center: { lat: 25, lng: 55 } });
    expect(map.setView).toHaveBeenCalledTimes(3);
  });
});
