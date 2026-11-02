import backend from "../api/backend";
import { setupStore } from "../app/store";
import { recordFetch, restoreFetch } from "../shell/testing";
import {
  MapSelectionContext,
  NewPackageContext,
  packageTarget,
  useInspectControlPoint,
  useInspectTgo,
  useNewPackage,
} from "./mapSelection";
import { renderHook } from "@testing-library/react";
import { PropsWithChildren } from "react";
import { Provider } from "react-redux";

afterEach(() => {
  restoreFetch();
  vi.restoreAllMocks();
});

function wrapper(select: ((s: unknown) => void) | null) {
  const store = setupStore();
  return ({ children }: PropsWithChildren) => (
    <Provider store={store}>
      <MapSelectionContext.Provider value={select}>
        {children}
      </MapSelectionContext.Provider>
    </Provider>
  );
}

describe("packageTarget", () => {
  it("maps each kind of selection to its package target", () => {
    expect(packageTarget(null)).toBeNull();
    expect(packageTarget({ kind: "controlPoint", id: "a" })).toEqual({
      target_kind: "control-point",
      target_id: "a",
    });
    expect(packageTarget({ kind: "tgo", id: "b" })).toEqual({
      target_kind: "tgo",
      target_id: "b",
    });
    expect(packageTarget({ kind: "frontLine", id: "c" })).toEqual({
      target_kind: "front-line",
      target_id: "c",
    });
    expect(packageTarget({ kind: "downedPilot", id: "d" })).toEqual({
      target_kind: "downed-pilot",
      target_id: "d",
    });
  });
});

describe("map right-clicks", () => {
  it("plan the package in the web editor in the web shell", () => {
    const post = vi.spyOn(backend, "post");
    const plan = vi.fn();
    const { result } = renderHook(() => useNewPackage(), {
      wrapper: ({ children }: PropsWithChildren) => (
        <NewPackageContext.Provider value={plan}>
          {children}
        </NewPackageContext.Provider>
      ),
    });
    result.current("front-line", "fl-1");
    expect(plan).toHaveBeenCalledWith({
      target_kind: "front-line",
      target_id: "fl-1",
    });
    expect(post).not.toHaveBeenCalled();
  });

});

describe("map clicks", () => {
  it("select the base for the inspector in the web shell", () => {
    const post = vi.spyOn(backend, "post");
    const select = vi.fn();
    const { result } = renderHook(() => useInspectControlPoint(), {
      wrapper: wrapper(select),
    });
    result.current("cp-1");
    expect(select).toHaveBeenCalledWith({ kind: "controlPoint", id: "cp-1" });
    expect(post).not.toHaveBeenCalled();
  });


  it("select the ground object in the web shell", () => {
    const calls = recordFetch();
    const select = vi.fn();
    const { result } = renderHook(() => useInspectTgo(), {
      wrapper: wrapper(select),
    });
    result.current("tgo-1");
    expect(select).toHaveBeenCalledWith({ kind: "tgo", id: "tgo-1" });
    expect(calls).toHaveLength(0);
  });

});
