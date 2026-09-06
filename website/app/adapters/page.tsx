import { DocShell } from "@/components/DocShell";
import { renderDoc } from "@/lib/docs";

export default async function Page() {
  return <DocShell href="/adapters" html={await renderDoc("adapters.md")} />;
}
