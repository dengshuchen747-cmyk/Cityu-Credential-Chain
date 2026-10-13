"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { shortWallet } from "@/lib/api";
import { useWallet } from "@/components/wallet-provider";

const links = [
  ["/school", "School"],
  ["/student", "Student"],
  ["/enterprise", "Enterprise"],
];

export function Navigation() {
  const pathname = usePathname();
  const { wallet, loading, connectAndSignIn, signOut } = useWallet();

  async function connect() {
    try {
      await connectAndSignIn();
    } catch (error) {
      alert(error instanceof Error ? error.message : "Wallet login failed");
    }
  }

  return (
    <header className="site-header">
      <Link className="brand" href="/">
        <span className="brand-mark">C</span>
        <span>CityU Credential Chain</span>
      </Link>
      <nav className="main-nav" aria-label="Choose your portal">
        {links.map(([href, label]) => (
          <Link
            className={pathname.startsWith(href) ? "active" : ""}
            href={href}
            key={href}
          >
            {label}
          </Link>
        ))}
      </nav>
      {wallet ? (
        <button className="wallet-button connected" onClick={signOut} title="Sign out">
          <span className="online-dot" /> {shortWallet(wallet)}
        </button>
      ) : (
        <button className="wallet-button" disabled={loading} onClick={connect}>
          {loading ? "Signing…" : "Connect wallet"}
        </button>
      )}
    </header>
  );
}
