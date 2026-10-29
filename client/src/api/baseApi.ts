import { API_KEY, API_KEY_HEADER, HTTP_URL, isCommandMethod } from "./backend";
import {
  BaseQueryFn,
  FetchArgs,
  FetchBaseQueryError,
  createApi,
  fetchBaseQuery,
} from "@reduxjs/toolkit/query/react";

const rawBaseQuery = fetchBaseQuery({ baseUrl: HTTP_URL });

/** Adds the API key (WEB-00.6) to every command sent by the generated hooks. */
export const baseQuery: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = (args, api, extraOptions) => {
  if (
    API_KEY === undefined ||
    typeof args === "string" ||
    !isCommandMethod(args.method)
  ) {
    return rawBaseQuery(args, api, extraOptions);
  }
  const headers = new Headers(args.headers as HeadersInit | undefined);
  headers.set(API_KEY_HEADER, API_KEY);
  return rawBaseQuery({ ...args, headers }, api, extraOptions);
};

export const baseApi = createApi({
  baseQuery,
  endpoints: () => ({}),
});
