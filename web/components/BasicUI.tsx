"use client";

import { createContext, HTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes, useContext, useState } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type Variant = "default" | "secondary" | "outline" | "ghost" | "destructive";
type ButtonSize = "default" | "xs" | "sm" | "lg" | "icon" | "icon-sm" | "icon-xs" | "icon-lg";

const buttonVariants: Record<Variant, string> = {
  default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/90",
  secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
  outline: "border-border bg-background hover:bg-muted",
  ghost: "border-transparent bg-transparent hover:bg-muted",
  destructive: "border-transparent bg-destructive/10 text-destructive hover:bg-destructive/20",
};

const buttonSizes: Record<ButtonSize, string> = {
  default: "h-9 px-3",
  xs: "h-7 px-2 text-xs",
  sm: "h-8 px-2.5 text-sm",
  lg: "h-10 px-4",
  icon: "size-9 p-0",
  "icon-sm": "size-8 p-0",
  "icon-xs": "size-7 p-0",
  "icon-lg": "size-10 p-0",
};

export function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: ButtonSize }) {
  return (
    <button
      className={cn(
        "inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border text-sm font-medium transition disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        buttonVariants[variant],
        buttonSizes[size],
        className,
      )}
      {...props}
    />
  );
}

export function Badge({
  className,
  variant = "default",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { variant?: "default" | "secondary" | "outline" | "destructive" }) {
  const classes = {
    default: "border-transparent bg-primary text-primary-foreground",
    secondary: "border-transparent bg-secondary text-secondary-foreground",
    outline: "border-border bg-background text-foreground",
    destructive: "border-transparent bg-destructive/10 text-destructive",
  }[variant];
  return <span className={cn("inline-flex min-h-5 w-fit items-center justify-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium", classes, className)} {...props} />;
}

export function Card({ className, size: _size, ...props }: HTMLAttributes<HTMLDivElement> & { size?: "default" | "sm" }) {
  return <div className={cn("flex flex-col gap-4 overflow-hidden rounded-xl border bg-card py-4 text-card-foreground", className)} {...props} />;
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("grid auto-rows-min items-start gap-1 px-4", className)} {...props} />;
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-4", className)} {...props} />;
}

export function CardAction({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("self-start justify-self-end", className)} {...props} />;
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("text-base leading-snug font-medium", className)} {...props} />;
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("text-sm text-muted-foreground", className)} {...props} />;
}

export function Alert({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div role="alert" className={cn("relative flex gap-3 rounded-xl border bg-card p-3 text-sm", className)} {...props} />;
}

export function AlertDescription({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("leading-6 text-muted-foreground", className)} {...props} />;
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn("h-9 w-full rounded-lg border border-input bg-background px-3 text-sm outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50", className)} {...props} />;
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn("min-h-20 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-50", className)} {...props} />;
}

export function Checkbox({
  className,
  checked,
  onCheckedChange,
  ...props
}: Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> & { onCheckedChange?: (checked: boolean) => void }) {
  return (
    <input
      type="checkbox"
      checked={Boolean(checked)}
      onChange={(event) => onCheckedChange?.(event.target.checked)}
      className={cn("size-4 rounded border border-input accent-primary", className)}
      {...props}
    />
  );
}

export function Separator({ className, orientation = "horizontal", ...props }: HTMLAttributes<HTMLDivElement> & { orientation?: "horizontal" | "vertical" }) {
  return <div className={cn("shrink-0 bg-border", orientation === "vertical" ? "w-px self-stretch" : "h-px w-full", className)} {...props} />;
}

export function ScrollArea({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("overflow-auto", className)} {...props} />;
}

export function Spinner({ className, ...props }: HTMLAttributes<SVGSVGElement>) {
  return <Loader2 role="status" aria-label="Loading" className={cn("size-4 animate-spin", className)} {...props} />;
}

export function Empty({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col items-center justify-center gap-3 rounded-xl p-6 text-center", className)} {...props} />;
}

export function EmptyMedia({ className, variant: _variant, ...props }: HTMLAttributes<HTMLDivElement> & { variant?: "icon" }) {
  return <div className={cn("flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground [&_svg]:size-6", className)} {...props} />;
}

export function EmptyHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col items-center gap-1", className)} {...props} />;
}

export function EmptyTitle({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("font-medium", className)} {...props} />;
}

export function EmptyDescription({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("max-w-sm text-sm text-muted-foreground", className)} {...props} />;
}

export function EmptyContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex items-center justify-center gap-2", className)} {...props} />;
}

export function FieldSet({ className, ...props }: React.FieldsetHTMLAttributes<HTMLFieldSetElement>) {
  return <fieldset className={cn("flex flex-col gap-4", className)} {...props} />;
}

export function FieldGroup({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col gap-4", className)} {...props} />;
}

export function Field({ className, orientation = "vertical", ...props }: HTMLAttributes<HTMLDivElement> & { orientation?: "vertical" | "horizontal" | "responsive" }) {
  return <div role="group" className={cn("flex w-full gap-2", orientation === "horizontal" ? "flex-row items-center" : "flex-col", className)} {...props} />;
}

export function FieldContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-1 flex-col gap-0.5", className)} {...props} />;
}

export function FieldLabel({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("text-sm font-medium leading-snug", className)} {...props} />;
}

export function FieldDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm leading-normal text-muted-foreground", className)} {...props} />;
}

type TabsContextValue = {
  value: string;
  setValue: (value: string) => void;
};

const TabsContext = createContext<TabsContextValue | null>(null);

export function Tabs({
  value,
  defaultValue,
  onValueChange,
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
}) {
  const [internalValue, setInternalValue] = useState(defaultValue || "");
  const currentValue = value ?? internalValue;
  const setValue = (next: string) => {
    if (value == null) setInternalValue(next);
    onValueChange?.(next);
  };
  return (
    <TabsContext.Provider value={{ value: currentValue, setValue }}>
      <div className={cn("flex flex-col gap-2", className)} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

export function TabsList({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div role="tablist" className={cn("inline-flex items-center justify-center rounded-lg bg-muted p-1", className)} {...props} />;
}

export function TabsTrigger({
  value,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { value: string }) {
  const context = useContext(TabsContext);
  const active = context?.value === value;
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      data-active={active ? "" : undefined}
      className={cn("inline-flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition hover:text-foreground data-active:bg-background data-active:text-foreground data-active:shadow-sm", className)}
      onClick={(event) => {
        props.onClick?.(event);
        context?.setValue(value);
      }}
      {...props}
    />
  );
}

export function TabsContent({
  value,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement> & { value: string }) {
  const context = useContext(TabsContext);
  if (context?.value !== value) return null;
  return <div role="tabpanel" className={cn("min-w-0", className)} {...props} />;
}
