"use client";

import { useEffect } from "react";

export const UNSAVED_CHANGES_MESSAGE = "Tenés cambios sin guardar. ¿Seguro que querés salir?";

export function useUnsavedChangesWarning(hasUnsavedChanges: boolean, message = UNSAVED_CHANGES_MESSAGE) {
  useEffect(() => {
    if (!hasUnsavedChanges) return;

    function handleBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = message;
      return message;
    }

    function handleDocumentClick(event: MouseEvent) {
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

      const target = event.target as Element | null;
      const link = target?.closest("a[href]") as HTMLAnchorElement | null;
      if (!link) return;

      const href = link.getAttribute("href");
      if (!href || href.startsWith("#") || link.target === "_blank" || link.hasAttribute("download")) return;

      const nextUrl = new URL(link.href, window.location.href);
      if (nextUrl.href === window.location.href) return;

      if (!window.confirm(message)) {
        event.preventDefault();
        event.stopPropagation();
      }
    }

    window.addEventListener("beforeunload", handleBeforeUnload);
    document.addEventListener("click", handleDocumentClick, true);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      document.removeEventListener("click", handleDocumentClick, true);
    };
  }, [hasUnsavedChanges, message]);
}
