"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = {
  href: string;
  label: string;
  isActive: (pathname: string) => boolean;
};

const navItems: NavItem[] = [
  {
    href: "/credit-dashboard",
    label: "Dashboard",
    isActive: (pathname) => pathname === "/credit-dashboard"
  },
  {
    href: "/what-if-analysis",
    label: "Analytics",
    isActive: (pathname) => pathname === "/what-if-analysis" || pathname === "/what-if"
  },
  {
    href: "/ai-processing",
    label: "Simulations",
    isActive: (pathname) =>
      pathname === "/ai-processing" ||
      pathname === "/processing" ||
      pathname === "/intake" ||
      pathname === "/persona-selection" ||
      pathname === "/demo"
  },
  {
    href: "/loan-marketplace",
    label: "Loans",
    isActive: (pathname) => pathname === "/loan-marketplace" || pathname === "/marketplace"
  }
];

type NotificationType = "loan" | "system" | "alert";
type NotificationTab = "all" | "unread" | "system";
type NotificationGroup = "Today" | "Earlier";

type NotificationItem = {
  id: string;
  type: NotificationType;
  message: string;
  timestamp: string;
  group: NotificationGroup;
  read: boolean;
};

type SettingsState = {
  account: {
    name: string;
    email: string;
    password: string;
    twoFactorEnabled: boolean;
  };
  platform: {
    defaultScoringModel: "Cred-ible v2" | "Hybrid AI + Rules" | "Conservative Rulebook";
    riskThreshold: number;
    region: "India" | "South East Asia" | "Middle East";
    currency: "INR" | "USD" | "AED";
  };
  notifications: {
    loanUpdates: boolean;
    systemAlerts: boolean;
    emailNotifications: boolean;
  };
  integrations: {
    apiKey: string;
    services: Array<{ id: string; label: string; status: "Connected" | "Disconnected" }>;
  };
  appearance: {
    theme: "dark" | "light";
  };
};

const initialNotifications: NotificationItem[] = [
  {
    id: "n1",
    type: "loan",
    message: "Loan application #L-2984 moved to underwriting.",
    timestamp: "10:14 AM",
    group: "Today",
    read: false
  },
  {
    id: "n2",
    type: "alert",
    message: "Risk threshold breach detected in SME segment.",
    timestamp: "9:42 AM",
    group: "Today",
    read: false
  },
  {
    id: "n3",
    type: "system",
    message: "Model sync completed successfully.",
    timestamp: "Yesterday",
    group: "Earlier",
    read: true
  }
];

const initialSettings: SettingsState = {
  account: {
    name: "Akash Sharma",
    email: "akash@credible.ai",
    password: "",
    twoFactorEnabled: true
  },
  platform: {
    defaultScoringModel: "Cred-ible v2",
    riskThreshold: 62,
    region: "India",
    currency: "INR"
  },
  notifications: {
    loanUpdates: true,
    systemAlerts: true,
    emailNotifications: false
  },
  integrations: {
    apiKey: "cred_live_8f7d2b9a4c11",
    services: [
      { id: "upi", label: "UPI", status: "Connected" },
      { id: "gst", label: "GST", status: "Connected" },
      { id: "bank", label: "Bank APIs", status: "Disconnected" }
    ]
  },
  appearance: {
    theme: "dark"
  }
};

function notificationTypeIcon(type: NotificationType) {
  if (type === "loan") {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="6" width="18" height="12" rx="2" />
        <path d="M7 12h10" />
      </svg>
    );
  }
  if (type === "alert") {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 9v4" />
        <path d="M12 17h.01" />
        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3l-8.47-14.14a2 2 0 0 0-3.42 0Z" />
      </svg>
    );
  }
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 6v6l4 2" />
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
}

export function AppHeader() {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [activeNotificationTab, setActiveNotificationTab] = useState<NotificationTab>("all");
  const [notifications, setNotifications] = useState<NotificationItem[]>(initialNotifications);
  const [savedSettings, setSavedSettings] = useState<SettingsState>(initialSettings);
  const [settingsDraft, setSettingsDraft] = useState<SettingsState>(initialSettings);
  const [isMobileProfileOpen, setIsMobileProfileOpen] = useState(false);
  const [isMobileNotificationsOpen, setIsMobileNotificationsOpen] = useState(false);
  const notificationsRef = useRef<HTMLDivElement | null>(null);
  const profileRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setIsMobileMenuOpen(false);
    setIsNotificationsOpen(false);
    setIsProfileOpen(false);
    setIsMobileNotificationsOpen(false);
    setIsMobileProfileOpen(false);
  }, [pathname]);

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") {
        return;
      }
      setIsNotificationsOpen(false);
      setIsProfileOpen(false);
      setIsSettingsOpen(false);
      setIsMobileProfileOpen(false);
      setIsMobileNotificationsOpen(false);
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (notificationsRef.current && !notificationsRef.current.contains(target)) {
        setIsNotificationsOpen(false);
      }
      if (profileRef.current && !profileRef.current.contains(target)) {
        setIsProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    document.documentElement.style.colorScheme = savedSettings.appearance.theme;
  }, [savedSettings.appearance.theme]);

  const filteredNotifications = useMemo(() => {
    if (activeNotificationTab === "unread") {
      return notifications.filter((notification) => !notification.read);
    }
    if (activeNotificationTab === "system") {
      return notifications.filter((notification) => notification.type === "system");
    }
    return notifications;
  }, [activeNotificationTab, notifications]);

  const groupedNotifications = useMemo(
    () => ({
      Today: filteredNotifications.filter((notification) => notification.group === "Today"),
      Earlier: filteredNotifications.filter((notification) => notification.group === "Earlier")
    }),
    [filteredNotifications]
  );

  const unreadCount = notifications.filter((notification) => !notification.read).length;

  const openSettings = () => {
    setSettingsDraft(savedSettings);
    setIsSettingsOpen(true);
    setIsNotificationsOpen(false);
    setIsProfileOpen(false);
  };

  const saveSettings = () => {
    setSavedSettings(settingsDraft);
    setIsSettingsOpen(false);
  };

  const closeSettings = () => {
    setSettingsDraft(savedSettings);
    setIsSettingsOpen(false);
  };

  const regenerateApiKey = () => {
    const nextKey = `cred_live_${Math.random().toString(16).slice(2, 14)}`;
    setSettingsDraft((previous) => ({
      ...previous,
      integrations: {
        ...previous.integrations,
        apiKey: nextKey
      }
    }));
  };

  const markAllNotificationsRead = () => {
    setNotifications((previous) => previous.map((notification) => ({ ...notification, read: true })));
  };

  return (
    <>
      <header className="app-header">
        <div className="app-header-inner grid w-full grid-cols-[auto_1fr_auto] items-center gap-3 md:gap-6">
          <Link
            href="/"
            className="text-2xl md:text-[1.75rem] leading-none font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400"
          >
            Cred-ible
          </Link>

          <nav className="hidden md:flex items-center justify-center gap-2 text-sm text-gray-400">
            {navItems.map((item) => {
              const active = item.isActive(pathname);
              const baseClass =
                "rounded-full border border-dashed px-3 py-1.5 font-semibold transition-all duration-200";
              const activeClass = "text-indigo-200 border-indigo-400/45 bg-indigo-500/12 shadow-[0_0_14px_rgba(129,140,248,0.35)]";
              const inactiveClass =
                "text-gray-400 border-indigo-500/0 hover:text-white hover:border-indigo-500/35 hover:bg-indigo-500/8 hover:shadow-[0_0_12px_rgba(129,140,248,0.25)]";

              return (
                <Link key={item.href} href={item.href} className={`${baseClass} ${active ? activeClass : inactiveClass}`}>
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center justify-end gap-4 text-gray-400 relative">
            <div className="hidden md:flex items-center gap-4">
              <div className="relative" ref={notificationsRef}>
                <button
                  className="hover:text-white transition-colors relative"
                  aria-label="Notifications"
                  onClick={() => {
                    setIsNotificationsOpen((previous) => !previous);
                    setIsProfileOpen(false);
                  }}
                >
                  {unreadCount > 0 ? <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-indigo-400" /> : null}
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
                    <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
                  </svg>
                </button>
                {isNotificationsOpen ? (
                  <div className="absolute right-0 mt-3 w-[360px] rounded-2xl border border-indigo-400/25 bg-slate-950/95 p-4 shadow-[0_24px_56px_rgba(0,0,0,0.55)] backdrop-blur-xl">
                    <div className="flex items-center justify-between border-b border-indigo-200/15 pb-3">
                      <p className="text-sm font-semibold text-white">Notifications</p>
                      <button className="text-xs text-indigo-200 hover:text-white" onClick={markAllNotificationsRead}>
                        Mark all as read
                      </button>
                    </div>
                    <div className="mt-3 flex items-center gap-2">
                      {(["all", "unread", "system"] as const).map((tab) => (
                        <button
                          key={tab}
                          className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase ${
                            activeNotificationTab === tab
                              ? "border-indigo-400/50 bg-indigo-500/20 text-indigo-100"
                              : "border-indigo-400/20 text-slate-300 hover:text-white"
                          }`}
                          onClick={() => setActiveNotificationTab(tab)}
                        >
                          {tab}
                        </button>
                      ))}
                    </div>
                    <div className="mt-4 max-h-[320px] overflow-auto pr-1">
                      {groupedNotifications.Today.length === 0 && groupedNotifications.Earlier.length === 0 ? (
                        <div className="rounded-xl border border-indigo-300/20 bg-slate-900/60 p-4 text-sm text-slate-400">
                          No notifications to show.
                        </div>
                      ) : (
                        <>
                          {groupedNotifications.Today.length > 0 ? (
                            <div className="mb-3">
                              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Today</p>
                              <div className="space-y-2">
                                {groupedNotifications.Today.map((notification) => (
                                  <div key={notification.id} className="rounded-xl border border-indigo-300/20 bg-slate-900/65 p-3">
                                    <div className="flex items-start gap-2.5">
                                      <span className="mt-0.5 text-indigo-200">{notificationTypeIcon(notification.type)}</span>
                                      <div className="flex-1">
                                        <p className="text-sm text-slate-100">{notification.message}</p>
                                        <p className="text-xs text-slate-400 mt-1">{notification.timestamp}</p>
                                      </div>
                                      {!notification.read ? <span className="h-2 w-2 rounded-full bg-indigo-400" /> : null}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : null}
                          {groupedNotifications.Earlier.length > 0 ? (
                            <div className="pt-3 border-t border-indigo-200/15">
                              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Earlier</p>
                              <div className="space-y-2">
                                {groupedNotifications.Earlier.map((notification) => (
                                  <div key={notification.id} className="rounded-xl border border-indigo-300/20 bg-slate-900/65 p-3">
                                    <div className="flex items-start gap-2.5">
                                      <span className="mt-0.5 text-indigo-200">{notificationTypeIcon(notification.type)}</span>
                                      <div className="flex-1">
                                        <p className="text-sm text-slate-100">{notification.message}</p>
                                        <p className="text-xs text-slate-400 mt-1">{notification.timestamp}</p>
                                      </div>
                                      {!notification.read ? <span className="h-2 w-2 rounded-full bg-indigo-400" /> : null}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : null}
                        </>
                      )}
                    </div>
                    <div className="mt-3 border-t border-indigo-200/15 pt-3">
                      <Link href="/result" className="text-sm text-indigo-200 hover:text-white">
                        View all notifications
                      </Link>
                    </div>
                  </div>
                ) : null}
              </div>
              <button className="hover:text-white transition-colors" aria-label="Settings" onClick={openSettings}>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </button>
              <div className="relative" ref={profileRef}>
                <button
                  className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center overflow-hidden hover:bg-slate-600 transition-colors"
                  aria-label="Profile"
                  onClick={() => {
                    setIsProfileOpen((previous) => !previous);
                    setIsNotificationsOpen(false);
                  }}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#94a3b8"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </button>
                {isProfileOpen ? (
                  <div className="absolute right-0 mt-3 w-[280px] rounded-2xl border border-indigo-400/25 bg-slate-950/95 p-3 shadow-[0_24px_56px_rgba(0,0,0,0.55)] backdrop-blur-xl">
                    <div className="rounded-xl border border-indigo-300/20 bg-slate-900/70 p-3 mb-2">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-indigo-500/25 text-indigo-100 flex items-center justify-center font-semibold">AS</div>
                        <div>
                          <p className="text-sm font-semibold text-slate-100">{savedSettings.account.name}</p>
                          <p className="text-xs text-slate-400">Credit Operations Lead</p>
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-col">
                      <Link href="/result" className="rounded-lg px-3 py-2 text-sm text-slate-200 hover:bg-indigo-500/15">My Profile</Link>
                      <Link href="/landing-page" className="rounded-lg px-3 py-2 text-sm text-slate-200 hover:bg-indigo-500/15">Team / Organization</Link>
                      <Link href="/loan-marketplace" className="rounded-lg px-3 py-2 text-sm text-slate-200 hover:bg-indigo-500/15">Billing / Subscription</Link>
                      <Link href="/landing-page" className="rounded-lg px-3 py-2 text-sm text-slate-200 hover:bg-indigo-500/15">Help / Documentation</Link>
                      <button className="text-left rounded-lg px-3 py-2 text-sm text-rose-300 hover:bg-rose-500/15">Logout</button>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
            <button
              type="button"
              aria-label="Toggle navigation menu"
              aria-expanded={isMobileMenuOpen}
              className="inline-flex md:hidden items-center justify-center rounded-xl border border-indigo-400/20 bg-indigo-400/10 p-2.5 text-indigo-100 transition-colors hover:bg-indigo-400/20"
              onClick={() => setIsMobileMenuOpen((previous) => !previous)}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                {isMobileMenuOpen ? (
                  <>
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </>
                ) : (
                  <>
                    <line x1="3" y1="6" x2="21" y2="6" />
                    <line x1="3" y1="12" x2="21" y2="12" />
                    <line x1="3" y1="18" x2="21" y2="18" />
                  </>
                )}
              </svg>
            </button>
          </div>
        </div>
      </header>
      <div
        className={`fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-[2px] transition-opacity duration-300 md:hidden ${
          isMobileMenuOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={() => setIsMobileMenuOpen(false)}
      />
      <aside
        className={`fixed left-0 top-0 z-50 flex h-dvh w-[80vw] max-w-[320px] flex-col border-r border-indigo-200/20 bg-gradient-to-b from-slate-900/60 via-slate-950/55 to-slate-950/70 p-5 shadow-[0_26px_80px_rgba(0,0,0,0.5)] backdrop-blur-2xl transition-transform duration-300 ease-out md:hidden ${
          isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-indigo-200/15 pb-4">
          <Link
            href="/"
            className="text-xl leading-none font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400"
          >
            Cred-ible
          </Link>
          <button
            type="button"
            aria-label="Close navigation menu"
            className="rounded-lg border border-indigo-300/20 bg-indigo-300/10 p-2 text-indigo-100 transition-colors hover:bg-indigo-300/20"
            onClick={() => setIsMobileMenuOpen(false)}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <nav className="mt-5 flex flex-1 flex-col gap-2">
          {navItems.map((item) => {
            const active = item.isActive(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-xl border px-4 py-3 text-sm font-semibold transition-all duration-200 ${
                  active
                    ? "border-indigo-400/45 bg-indigo-500/20 text-indigo-100 shadow-[0_0_14px_rgba(129,140,248,0.35)]"
                    : "border-indigo-400/0 bg-transparent text-slate-300 hover:border-indigo-400/30 hover:bg-indigo-500/10 hover:text-white"
                }`}
              >
export function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="app-header">
      <div className="app-header-inner grid w-full grid-cols-[auto_1fr_auto] items-center gap-3 md:gap-6">
        <Link
          href="/"
          className="text-2xl md:text-[1.75rem] leading-none font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400"
        >
          Cred-ible
        </Link>

        <nav className="hidden md:flex items-center justify-center gap-2 text-sm text-gray-400">
          {navItems.map((item) => {
            const active = item.isActive(pathname);
            const baseClass =
              "rounded-full border border-dashed px-3 py-1.5 font-semibold transition-all duration-200";
            const activeClass = "text-indigo-200 border-indigo-400/45 bg-indigo-500/12 shadow-[0_0_14px_rgba(129,140,248,0.35)]";
            const inactiveClass =
              "text-gray-400 border-indigo-500/0 hover:text-white hover:border-indigo-500/35 hover:bg-indigo-500/8 hover:shadow-[0_0_12px_rgba(129,140,248,0.25)]";

            return (
              <Link key={item.href} href={item.href} className={`${baseClass} ${active ? activeClass : inactiveClass}`}>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-4 flex items-center gap-3 border-t border-indigo-200/15 pt-4">
          <button
            type="button"
            aria-label="Settings"
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-300/20 bg-indigo-300/10 text-indigo-100 transition-colors hover:bg-indigo-300/20"
            onClick={openSettings}
          >

        <div className="flex items-center justify-end gap-4 text-gray-400">
          <button className="hover:text-white transition-colors" aria-label="Notifications">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </button>
          <button
            type="button"
            aria-label="Profile"
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-300/20 bg-indigo-300/10 text-indigo-100 transition-colors hover:bg-indigo-300/20"
            onClick={() => setIsMobileProfileOpen((previous) => !previous)}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
              <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
            </svg>
          </button>
          <button className="hover:text-white transition-colors" aria-label="Settings">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </button>
          <button
            type="button"
            aria-label="Notifications"
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-300/20 bg-indigo-300/10 text-indigo-100 transition-colors hover:bg-indigo-300/20 relative"
            onClick={() => setIsMobileNotificationsOpen((previous) => !previous)}
          >
            {unreadCount > 0 ? <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-indigo-300" /> : null}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </button>
          <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center overflow-hidden">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#94a3b8"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
              <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
            </svg>
          </button>
        </div>
        {isMobileNotificationsOpen ? (
          <div className="mt-4 rounded-xl border border-indigo-300/20 bg-slate-900/60 p-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-100">Notifications</p>
              <button className="text-xs text-indigo-200" onClick={markAllNotificationsRead}>
                Mark all as read
              </button>
            </div>
            <div className="mt-3 space-y-2">
              {notifications.length === 0 ? <p className="text-xs text-slate-400">No notifications to show.</p> : null}
              {notifications.slice(0, 3).map((notification) => (
                <div key={notification.id} className="rounded-lg border border-indigo-300/20 bg-slate-950/60 p-2">
                  <p className="text-xs text-slate-100">{notification.message}</p>
                  <p className="text-[11px] text-slate-400 mt-1">{notification.timestamp}</p>
                </div>
              ))}
            </div>
          </div>
        ) : null}
        {isMobileProfileOpen ? (
          <div className="mt-4 rounded-xl border border-indigo-300/20 bg-slate-900/60 p-3">
            <p className="text-sm font-semibold text-slate-100">{savedSettings.account.name}</p>
            <p className="text-xs text-slate-400 mb-2">Credit Operations Lead</p>
            <div className="flex flex-col">
              <Link href="/result" className="rounded-lg px-2 py-1.5 text-sm text-slate-200 hover:bg-indigo-500/15">My Profile</Link>
              <Link href="/landing-page" className="rounded-lg px-2 py-1.5 text-sm text-slate-200 hover:bg-indigo-500/15">Team / Organization</Link>
              <Link href="/loan-marketplace" className="rounded-lg px-2 py-1.5 text-sm text-slate-200 hover:bg-indigo-500/15">Billing / Subscription</Link>
              <Link href="/landing-page" className="rounded-lg px-2 py-1.5 text-sm text-slate-200 hover:bg-indigo-500/15">Help / Documentation</Link>
              <button className="text-left rounded-lg px-2 py-1.5 text-sm text-rose-300 hover:bg-rose-500/15">Logout</button>
            </div>
          </div>
        ) : null}
      </aside>
      {isSettingsOpen ? (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm" onClick={closeSettings} />
          <div className="relative w-full max-w-[860px] max-h-[88vh] overflow-auto rounded-3xl border border-indigo-300/25 bg-slate-950/95 p-5 md:p-6 shadow-[0_30px_70px_rgba(0,0,0,0.6)]">
            <div className="flex items-center justify-between pb-4 border-b border-indigo-200/15">
              <h2 className="text-lg font-semibold text-white">Settings</h2>
              <button className="text-slate-300 hover:text-white" aria-label="Close settings" onClick={closeSettings}>
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-5">
              <section className="rounded-2xl border border-indigo-300/20 bg-slate-900/55 p-4">
                <h3 className="text-sm font-semibold text-indigo-100 mb-3">1. Account</h3>
                <div className="space-y-3">
                  <label className="form-label">
                    Name
                    <input
                      className="form-input"
                      value={settingsDraft.account.name}
                      onChange={(event) =>
                        setSettingsDraft((previous) => ({
                          ...previous,
                          account: { ...previous.account, name: event.target.value }
                        }))
                      }
                    />
                  </label>
                  <label className="form-label">
                    Email
                    <input
                      className="form-input"
                      value={settingsDraft.account.email}
                      onChange={(event) =>
                        setSettingsDraft((previous) => ({
                          ...previous,
                          account: { ...previous.account, email: event.target.value }
                        }))
                      }
                    />
                  </label>
                  <label className="form-label">
                    Change password
                    <input
                      type="password"
                      className="form-input"
                      value={settingsDraft.account.password}
                      onChange={(event) =>
                        setSettingsDraft((previous) => ({
                          ...previous,
                          account: { ...previous.account, password: event.target.value }
                        }))
                      }
                      placeholder="Enter new password"
                    />
                  </label>
                  <label className="flex items-center justify-between text-sm text-slate-200">
                    2FA
                    <button
                      type="button"
                      className={`h-6 w-11 rounded-full p-1 transition-colors ${
                        settingsDraft.account.twoFactorEnabled ? "bg-indigo-500/70" : "bg-slate-600"
                      }`}
                      onClick={() =>
                        setSettingsDraft((previous) => ({
                          ...previous,
                          account: { ...previous.account, twoFactorEnabled: !previous.account.twoFactorEnabled }
                        }))
                      }
                    >
                      <span
                        className={`block h-4 w-4 rounded-full bg-white transition-transform ${
                          settingsDraft.account.twoFactorEnabled ? "translate-x-5" : "translate-x-0"
                        }`}
                      />
                    </button>
                  </label>
                </div>
              </section>
              <section className="rounded-2xl border border-indigo-300/20 bg-slate-900/55 p-4">
                <h3 className="text-sm font-semibold text-indigo-100 mb-3">2. Platform</h3>
                <div className="space-y-3">
                  <label className="form-label">
                    Default scoring model
                    <select
                      className="form-select"
                      value={settingsDraft.platform.defaultScoringModel}
                      onChange={(event) =>
                        setSettingsDraft((previous) => ({
                          ...previous,
                          platform: {
                            ...previous.platform,
                            defaultScoringModel: event.target.value as SettingsState["platform"]["defaultScoringModel"]
                          }
                        }))
                      }
                    >
                      <option>Cred-ible v2</option>
                      <option>Hybrid AI + Rules</option>
                      <option>Conservative Rulebook</option>
                    </select>
                  </label>
                  <label className="form-label">
                    Risk threshold ({settingsDraft.platform.riskThreshold})
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={settingsDraft.platform.riskThreshold}
                      onChange={(event) =>
                        setSettingsDraft((previous) => ({
                          ...previous,
                          platform: { ...previous.platform, riskThreshold: Number(event.target.value) }
                        }))
                      }
                    />
                    <input
                      type="number"
                      min={0}
                      max={100}
                      className="form-input"
                      value={settingsDraft.platform.riskThreshold}
                      onChange={(event) =>
                        setSettingsDraft((previous) => ({
                          ...previous,
                          platform: { ...previous.platform, riskThreshold: Number(event.target.value) || 0 }
                        }))
                      }
                    />
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <label className="form-label">
                      Region
                      <select
                        className="form-select"
                        value={settingsDraft.platform.region}
                        onChange={(event) =>
                          setSettingsDraft((previous) => ({
                            ...previous,
                            platform: {
                              ...previous.platform,
                              region: event.target.value as SettingsState["platform"]["region"]
                            }
                          }))
                        }
                      >
                        <option>India</option>
                        <option>South East Asia</option>
                        <option>Middle East</option>
                      </select>
                    </label>
                    <label className="form-label">
                      Currency
                      <select
                        className="form-select"
                        value={settingsDraft.platform.currency}
                        onChange={(event) =>
                          setSettingsDraft((previous) => ({
                            ...previous,
                            platform: {
                              ...previous.platform,
                              currency: event.target.value as SettingsState["platform"]["currency"]
                            }
                          }))
                        }
                      >
                        <option>INR</option>
                        <option>USD</option>
                        <option>AED</option>
                      </select>
                    </label>
                  </div>
                </div>
              </section>
              <section className="rounded-2xl border border-indigo-300/20 bg-slate-900/55 p-4">
                <h3 className="text-sm font-semibold text-indigo-100 mb-3">3. Notifications</h3>
                <div className="space-y-2">
                  {[
                    { key: "loanUpdates", label: "Loan updates" },
                    { key: "systemAlerts", label: "System alerts" },
                    { key: "emailNotifications", label: "Email notifications" }
                  ].map((item) => (
                    <label key={item.key} className="flex items-center justify-between rounded-xl border border-indigo-300/20 px-3 py-2 text-sm text-slate-200">
                      {item.label}
                      <input
                        type="checkbox"
                        checked={settingsDraft.notifications[item.key as keyof SettingsState["notifications"]]}
                        onChange={() =>
                          setSettingsDraft((previous) => ({
                            ...previous,
                            notifications: {
                              ...previous.notifications,
                              [item.key]: !previous.notifications[item.key as keyof SettingsState["notifications"]]
                            }
                          }))
                        }
                      />
                    </label>
                  ))}
                </div>
              </section>
              <section className="rounded-2xl border border-indigo-300/20 bg-slate-900/55 p-4">
                <h3 className="text-sm font-semibold text-indigo-100 mb-3">4. Integrations</h3>
                <div className="space-y-3">
                  <label className="form-label">
                    API key
                    <div className="flex gap-2">
                      <input className="form-input" value={settingsDraft.integrations.apiKey} readOnly />
                      <button className="btn-secondary rounded-xl px-3 py-2 text-xs" onClick={regenerateApiKey}>
                        Regenerate
                      </button>
                    </div>
                  </label>
                  <div className="space-y-2">
                    {settingsDraft.integrations.services.map((service) => (
                      <div key={service.id} className="flex items-center justify-between rounded-xl border border-indigo-300/20 px-3 py-2 text-sm">
                        <span className="text-slate-200">{service.label}</span>
                        <span className="inline-flex items-center gap-2 text-xs text-slate-300">
                          <span
                            className={`h-2 w-2 rounded-full ${
                              service.status === "Connected" ? "bg-emerald-400" : "bg-amber-400"
                            }`}
                          />
                          {service.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
              <section className="rounded-2xl border border-indigo-300/20 bg-slate-900/55 p-4 md:col-span-2">
                <h3 className="text-sm font-semibold text-indigo-100 mb-3">5. Appearance</h3>
                <div className="flex items-center justify-between rounded-xl border border-indigo-300/20 px-3 py-2 text-sm text-slate-200">
                  Theme
                  <div className="flex items-center gap-2">
                    <button
                      className={`rounded-lg px-3 py-1.5 text-xs ${settingsDraft.appearance.theme === "dark" ? "bg-indigo-500/30 text-indigo-100" : "bg-slate-800 text-slate-300"}`}
                      onClick={() =>
                        setSettingsDraft((previous) => ({
                          ...previous,
                          appearance: { ...previous.appearance, theme: "dark" }
                        }))
                      }
                    >
                      Dark
                    </button>
                    <button
                      className={`rounded-lg px-3 py-1.5 text-xs ${settingsDraft.appearance.theme === "light" ? "bg-indigo-500/30 text-indigo-100" : "bg-slate-800 text-slate-300"}`}
                      onClick={() =>
                        setSettingsDraft((previous) => ({
                          ...previous,
                          appearance: { ...previous.appearance, theme: "light" }
                        }))
                      }
                    >
                      Light
                    </button>
                  </div>
                </div>
              </section>
            </div>
            <div className="mt-5 flex items-center justify-end gap-3 border-t border-indigo-200/15 pt-4">
              <button className="btn-ghost rounded-xl px-4 py-2 text-sm" onClick={closeSettings}>
                Cancel
              </button>
              <button className="btn-primary rounded-xl px-4 py-2 text-sm" onClick={saveSettings}>
                Save
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
              <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
        </div>
      </div>
    </header>
  );
}
