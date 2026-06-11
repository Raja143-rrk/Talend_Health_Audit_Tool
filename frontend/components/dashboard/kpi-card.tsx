"use client";

import { useEffect, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { motion, useMotionValue, useSpring } from "framer-motion";

import { cn } from "@/lib/utils";

type KpiCardProps = {
  title: string;
  value: number;
  suffix?: string;
  change?: string;
  tone: "cyan" | "emerald" | "red" | "amber" | "blue" | "violet";
  icon: LucideIcon;
  subtitle?: string;
  onClick?: () => void;
};

const toneAccent = {
  cyan: "from-cyan-500/20 to-cyan-600/5 border-cyan-500/30",
  emerald: "from-emerald-500/20 to-emerald-600/5 border-emerald-500/30",
  red: "from-red-500/20 to-red-600/5 border-red-500/30",
  amber: "from-amber-500/20 to-amber-600/5 border-amber-500/30",
  blue: "from-blue-500/20 to-blue-600/5 border-blue-500/30",
  violet: "from-violet-500/20 to-violet-600/5 border-violet-500/30",
};

const toneIconBg = {
  cyan: "bg-cyan-500/15 text-cyan-600 dark:text-cyan-300",
  emerald: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300",
  red: "bg-red-500/15 text-red-600 dark:text-red-300",
  amber: "bg-amber-500/15 text-amber-600 dark:text-amber-300",
  blue: "bg-blue-500/15 text-blue-600 dark:text-blue-300",
  violet: "bg-violet-500/15 text-violet-600 dark:text-violet-300",
};

const toneGlow = {
  cyan: "shadow-cyan-500/10",
  emerald: "shadow-emerald-500/10",
  red: "shadow-red-500/10",
  amber: "shadow-amber-500/10",
  blue: "shadow-blue-500/10",
  violet: "shadow-violet-500/10",
};

function AnimatedNumber({ value, suffix = "" }: { value: number; suffix?: string }) {
  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { stiffness: 80, damping: 18 });
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    motionValue.set(value);
  }, [motionValue, value]);

  useEffect(() => {
    const unsubscribe = spring.on("change", (latest) => {
      setDisplayValue(Math.round(latest));
    });

    return unsubscribe;
  }, [spring]);

  return (
    <span>
      {displayValue.toLocaleString()}
      {suffix}
    </span>
  );
}

export function KpiCard({
  title,
  value,
  suffix,
  change,
  tone,
  icon: Icon,
  subtitle,
  onClick,
}: KpiCardProps) {
  return (
    <motion.article
      className={cn(
        "group relative overflow-hidden rounded-2xl border bg-gradient-to-br p-5 shadow-lg backdrop-blur-xl transition-all",
        "dark:border-white/10",
        toneAccent[tone],
        toneGlow[tone],
        "bg-white/80 dark:bg-slate-950/80",
        onClick && "cursor-pointer",
      )}
      whileHover={{ y: -4, scale: 1.02 }}
      transition={{ duration: 0.2 }}
      onClick={onClick}
    >
      <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-gradient-to-br from-white/40 to-transparent blur-2xl dark:from-white/5" />
      <div className="relative">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              {title}
            </p>
            <p className="mt-2 text-3xl font-bold text-slate-950 dark:text-white">
              <AnimatedNumber value={value} suffix={suffix} />
            </p>
            {subtitle ? (
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                {subtitle}
              </p>
            ) : null}
          </div>
          <div className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-xl shadow-sm backdrop-blur-sm", toneIconBg[tone])}>
            <Icon className="h-5 w-5" />
          </div>
        </div>

        {change ? (
          <div className="mt-4 flex items-center gap-2 text-sm">
            <span className="text-xs font-medium text-slate-400">Status</span>
            <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700 dark:bg-white/10 dark:text-slate-200">
              {change}
            </span>
          </div>
        ) : null}
      </div>
    </motion.article>
  );
}
