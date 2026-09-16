import { Loader2 } from "lucide-react";

export function LoadingSpinner({
  size = "default",
  className,
  text,
}: {
  size?: "sm" | "default" | "lg";
  className?: string;
  text?: string;
}) {
  const sizeClasses = {
    sm: "h-4 w-4",
    default: "h-8 w-8",
    lg: "h-12 w-12",
  };

  return (
    <div
      className={`flex flex-col items-center justify-center space-y-2 ${className || ""}`}
    >
      <Loader2 className={`animate-spin text-primary ${sizeClasses[size]}`} />
      {text && <p className="text-sm text-muted-foreground">{text}</p>}
    </div>
  );
}
