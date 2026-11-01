import backend from "../api/backend";
import { setupStore } from "../app/store";
import { recordFetch, restoreFetch } from "../shell/testing";
import {
  MapSelectionContext,
  NewPackageContext,
  useInspectControlPoint,
  useInspectTgo,
  useNewPackage,
} from "./mapSelection";
import { renderHook, waitFor } from "@testing-library/react";
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

  it.each(["control-point", "tgo", "front-line", "downed-pilot"] as const)(
    "open the Qt dialog on a %s in the Qt map",
    (kind) => {
      const post = vi
        .spyOn(backend, "post")
        .mockResolvedValue({ data: null } as never);
      const { result } = renderHook(() => useNewPackage());
      result.current(kind, "id-1");
      expect(post).toHaveBeenCalledWith(`/qt/create-package/${kind}/id-1`);
    },
  );
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

  it("open the Qt base dialog in the Qt map", () => {
    const post = vi
      .spyOn(backend, "post")
      .mockResolvedValue({ data: null } as never);
    const { result } = renderHook(() => useInspectControlPoint(), {
      wrapper: wrapper(null),
    });
    result.current("cp-1");
    expect(post).toHaveBeenCalledWith("/qt/info/control-point/cp-1");
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

  it("open the Qt ground object dialog in the Qt map", async () => {
    const calls = recordFetch();
    const { result } = renderHook(() => useInspectTgo(), {
      wrapper: wrapper(null),
    });
    result.current("tgo-1");
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0].path).toBe("/qt/info/tgo/tgo-1");
  });
});
