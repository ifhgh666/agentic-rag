import { act, type ReactNode } from "react";
import { createRoot } from "react-dom/client";

export function prepareDom() {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  window.matchMedia ??= (query) => ({ matches:false, media:query, onchange:null, addListener(){}, removeListener(){}, addEventListener(){}, removeEventListener(){}, dispatchEvent:()=>true });
}
export async function mount(element: ReactNode) {
  const container=document.createElement("div"); document.body.append(container);
  const root=createRoot(container); await act(async()=>root.render(element));
  return { container, root, unmount:async()=>{await act(async()=>root.unmount());container.remove();} };
}
export async function setInput(field: HTMLInputElement,value:string) {
  await act(async()=>{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value")!.set!.call(field,value);field.dispatchEvent(new Event("input",{bubbles:true}));});
}
