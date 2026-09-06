import { DocShell } from "@/components/DocShell";
import { renderDoc } from "@/lib/docs";

export default async function Page() {
  return <DocShell href="/cli" html={await renderDoc("cli.md")} />;
}
