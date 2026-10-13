import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { Navigation } from "@/components/navigation";
import { WalletProvider } from "@/components/wallet-provider";

export const metadata: Metadata = {
  title: "CityU Credential Chain",
  description: "CityU activities and publicly verifiable student credentials.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <WalletProvider>
          <Navigation />
          <main>{children}</main>
          <footer className="site-footer">
            <div>
              <strong>CityU Credential Chain</strong>
              <span>Academic proof, owned by students.</span>
            </div>
            <div className="footer-links">
              <Link href="/student">Student wallet</Link>
              <Link href="/enterprise">Enterprise lookup</Link>
              <a href="https://sepolia.etherscan.io" target="_blank" rel="noreferrer">
                Sepolia ↗
              </a>
            </div>
          </footer>
        </WalletProvider>
      </body>
    </html>
  );
}
