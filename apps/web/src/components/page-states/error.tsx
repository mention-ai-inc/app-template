import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { AlertCircle, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

export function ErrorComponent({
  title = "Something went wrong",
  error,
  className,
  fullScreen = false,
}: {
  title?: string;
  error: Error | string | unknown;
  className?: string;
  fullScreen?: boolean;
}) {
  const [showDetails, setShowDetails] = useState(false);

  let message = "";
  if (error instanceof Error) {
    message = error.message;
  } else if (typeof error === "string") {
    message = error;
  } else {
    message = "An unknown error occurred";
  }

  const containerClasses = fullScreen
    ? "fixed inset-0 flex items-center justify-center bg-black/5 backdrop-blur-sm z-50"
    : "flex items-start justify-center w-full h-full min-h-[50vh] pt-[20vh] p-8";

  return (
    <div className={containerClasses}>
      <Alert variant="destructive" className={`max-w-md ${className ?? ""}`}>
        <AlertCircle />
        <AlertTitle>{title}</AlertTitle>
        <AlertDescription>
          <p>
            We ran into a problem. Try refreshing the page, or contact support
            if this keeps happening.
          </p>
          <Button
            variant="ghost"
            size="sm"
            className="mt-2 h-auto p-0 text-xs text-destructive/70 hover:text-destructive hover:bg-transparent"
            onClick={() => setShowDetails((v) => !v)}
          >
            {showDetails ? "Hide error details" : "Show error details"}
            {showDetails ? (
              <ChevronUp className="h-3 w-3 ml-1" />
            ) : (
              <ChevronDown className="h-3 w-3 ml-1" />
            )}
          </Button>
          {showDetails && (
            <pre className="mt-2 text-xs bg-destructive/5 border border-destructive/20 rounded p-2 whitespace-pre-wrap break-all">
              {message}
            </pre>
          )}
        </AlertDescription>
      </Alert>
    </div>
  );
}
