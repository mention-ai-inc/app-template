import { LoadingSpinner } from "@/components/ui/loading-spinner";

export function LoadingComponent({
  text = "Loading...",
  className,
}: {
  text?: string;
  className?: string;
}) {
  return (
    <div className="flex items-center justify-center min-h-screen w-full">
      <LoadingSpinner text={text} className={className} />
    </div>
  );
}

export function PageLoading({
  text = "Loading...",
  className,
  minHeight = "min-h-[400px]",
}: {
  text?: string;
  className?: string;
  minHeight?: string;
}) {
  return (
    <div
      className={`flex items-center justify-center w-full ${minHeight} ${className || ""}`}
    >
      <LoadingSpinner text={text} />
    </div>
  );
}
