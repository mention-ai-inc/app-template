import { useEffect } from "react";

export function CmdEnterSubmitHandler() {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        const target = e.target as HTMLElement;
        const form = target?.closest?.("form");
        if (form && form.querySelector('button[type="submit"]')) {
          e.preventDefault();
          form.requestSubmit();
        }
      }
    };
    document.addEventListener("keydown", handleKeyDown, true);
    return () => document.removeEventListener("keydown", handleKeyDown, true);
  }, []);
  return null;
}
