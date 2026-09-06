import { DocShell } from "@/components/DocShell";
import { renderDoc } from "@/lib/docs";

export default async function Page() {
  return <DocShell href="/python-api" html={await renderDoc("python-api.md")} />;
}
