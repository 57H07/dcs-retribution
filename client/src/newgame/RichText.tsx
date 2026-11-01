// Campaign and faction files hold simple HTML. It comes from user-editable files:
// only a short list of tags becomes elements, everything else becomes plain text.
import { createElement, Fragment, ReactNode } from "react";

const ALLOWED = new Set([
  "p",
  "br",
  "strong",
  "b",
  "em",
  "i",
  "u",
  "ul",
  "ol",
  "li",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
]);

function render(node: Node, key: number): ReactNode {
  if (node.nodeType === Node.TEXT_NODE) {
    return node.textContent;
  }
  if (node.nodeType !== Node.ELEMENT_NODE) {
    return null;
  }
  const children = Array.from(node.childNodes).map(render);
  const tag = node.nodeName.toLowerCase();
  if (tag === "br") {
    return <br key={key} />;
  }
  return ALLOWED.has(tag) ? (
    createElement(tag, { key }, ...children)
  ) : (
    <Fragment key={key}>{children}</Fragment>
  );
}

export function RichText({ html }: { html: string }) {
  const parsed = new DOMParser().parseFromString(html, "text/html");
  return <>{Array.from(parsed.body.childNodes).map(render)}</>;
}
