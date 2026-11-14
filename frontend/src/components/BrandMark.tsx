import { BookOpen } from "lucide-react";
import { cn } from "cn";

export function BrandMark({ className }: { className?: string }) {
  return <span aria-hidden="true" className={cn("inline-flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground", className)}>
    <BookOpen className="size-6" strokeWidth={1.6} />
  </span>;
}
