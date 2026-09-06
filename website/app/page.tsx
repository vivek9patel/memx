import { DocShell } from "@/components/DocShell";
import { renderDoc } from "@/lib/docs";

export default async function HomePage() {
  return <DocShell href="/" html={await renderDoc("README.md")} />;
}
