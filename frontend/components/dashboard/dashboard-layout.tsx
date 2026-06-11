"use client";

import type { ReactNode } from "react";
import { useState } from "react";
import {
  BarChart3,
  Bell,
  Bot,
  ChevronLeft,
  Gauge,
  LayoutDashboard,
  Menu,
  Package,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  UserCircle,
  FileText,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export type DashboardSection =
  | "Dashboard"
  | "AI Chat"
  | "Security"
  | "Performance"
  | "Components"
  | "Recommendations"
  | "AI Agents"
  | "Reports"
  | "Settings";

const menus = [
  { label: "Dashboard", icon: LayoutDashboard },
  { label: "AI Chat", icon: Sparkles },
  { label: "Security", icon: ShieldCheck },
  { label: "Performance", icon: Gauge },
  { label: "Components", icon: Package },
  { label: "Recommendations", icon: Sparkles },
  { label: "AI Agents", icon: Bot },
  { label: "Reports", icon: FileText },
  { label: "Settings", icon: Settings },
];

type DashboardLayoutProps = {
  children: ReactNode;
  activeSection?: DashboardSection;
  onSectionChange?: (section: DashboardSection) => void;
};

export function DashboardLayout({
  children,
  activeSection = "Dashboard",
  onSectionChange,
}: DashboardLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="h-screen overflow-hidden bg-slate-100 text-slate-950 dark:bg-slate-950 dark:text-white">
      <div className="relative flex h-full">
        <AnimatePresence>
          {mobileOpen ? (
            <motion.button
              type="button"
              aria-label="Close sidebar"
              className="fixed inset-0 z-30 bg-slate-950/40 backdrop-blur-sm lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
            />
          ) : null}
        </AnimatePresence>

        <motion.aside
          className={cn(
            "fixed inset-y-0 left-0 z-40 border-r border-slate-200 bg-white shadow-xl shadow-slate-900/5 dark:border-white/10 dark:bg-slate-950 lg:sticky lg:top-0",
            mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
          )}
          animate={{ width: collapsed ? 88 : 284 }}
          transition={{ duration: 0.24, ease: "easeOut" }}
        >
          <div className="flex h-full flex-col p-4">
            <div className="flex h-14 items-center justify-between">
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-cyan-600 text-sm font-bold text-white shadow-lg shadow-cyan-600/25">
                  TH
                </div>
                {!collapsed ? (
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold">Talend Health</p>
                  </div>
                ) : null}
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="hidden lg:inline-flex"
                aria-label="Collapse sidebar"
                onClick={() => setCollapsed((value) => !value)}
              >
                <ChevronLeft
                  className={cn("h-4 w-4 transition", collapsed && "rotate-180")}
                />
              </Button>
            </div>

            <nav className="mt-8 space-y-1">
              {menus.map((item, index) => {
                const Icon = item.icon;
                return (
                  <motion.button
                    key={item.label}
                    type="button"
                    className={cn(
                      "flex h-11 w-full items-center gap-3 rounded-lg px-3 text-left text-sm font-medium transition",
                      item.label === activeSection
                        ? "bg-slate-950 text-white shadow-sm dark:bg-white dark:text-slate-950"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white",
                      collapsed && "justify-center px-0",
                    )}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.035 }}
                    onClick={() => {
                      onSectionChange?.(item.label as DashboardSection);
                      setMobileOpen(false);
                    }}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {!collapsed ? <span className="truncate">{item.label}</span> : null}
                  </motion.button>
                );
              })}
            </nav>

            <div className="mt-auto rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
              {!collapsed ? (
                <>
                  <p className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                    Workspace
                  </p>
                  <p className="mt-2 text-sm font-semibold">Health Audit</p>
                </>
              ) : (
                <BarChart3 className="mx-auto h-5 w-5 text-slate-600 dark:text-slate-300" />
              )}
            </div>
          </div>
        </motion.aside>

        <div className="flex min-w-0 flex-1 flex-col min-h-0">
          <header className="sticky top-0 z-20 border-b border-slate-200 bg-white px-4 py-3 dark:border-white/10 dark:bg-slate-950 sm:px-6">
            <div className="flex items-center gap-3">
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="lg:hidden"
                aria-label="Open sidebar"
                onClick={() => setMobileOpen(true)}
              >
                <Menu className="h-4 w-4" />
              </Button>

              <div className="relative min-w-0 flex-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  type="search"
                  placeholder="Search jobs, components, reports"
                  className="pl-9"
                />
              </div>

              <Button type="button" variant="outline" size="icon" aria-label="Notifications">
                <Bell className="h-4 w-4" />
              </Button>
              <ThemeToggle />

              <div className="hidden items-center gap-3 rounded-lg border border-slate-200 bg-white/70 px-3 py-2 dark:border-white/10 dark:bg-white/5 sm:flex">
                <UserCircle className="h-7 w-7 text-slate-500 dark:text-slate-300" />
                <div className="leading-tight">
                  <p className="text-sm font-semibold">Admin</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Platform
                  </p>
                </div>
              </div>
            </div>
          </header>

          <motion.main
            className="min-w-0 flex-1 min-h-0 overflow-y-auto p-4 sm:p-6"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
          >
            {children}
          </motion.main>
        </div>
      </div>
    </div>
  );
}
