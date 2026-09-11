import { Button } from "@/components/ui/button";
import { Link } from "@tanstack/react-router";

export function NotFoundComponent() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] text-center p-8">
      <h1 className="mb-4 font-serif text-4xl leading-tight tracking-tight">
        Not Found
      </h1>
      <p className="text-muted-foreground mb-6">
        The page you're looking for seems to have wandered off...
      </p>
      <Button asChild>
        <Link to="/">Go Back Home</Link>
      </Button>
    </div>
  );
}
