import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center justify-center font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-muted text-muted-foreground",
        success: "bg-success/12 text-success",
        warning: "bg-warning/15 text-warning",
        info: "bg-info/12 text-info",
        destructive: "bg-destructive/12 text-destructive",
        outline: "border border-border text-foreground",
      },
      size: {
        default: "rounded-md px-2 py-0.5 text-xs",
        sm: "rounded px-1.5 py-0.5 text-[10px]",
        compact: "size-6 rounded text-[10px]",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

function Badge({
  className,
  variant,
  size,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return (
    <span
      data-slot="badge"
      className={cn(badgeVariants({ variant, size }), className)}
      {...props}
    />
  );
}

export { Badge, badgeVariants };
