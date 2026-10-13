"use client";

import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { apiFetch } from "@/lib/api";
import type { ChainTransaction } from "@/lib/types";

type EthereumProvider = {
  request: (request: { method: string; params?: unknown[] }) => Promise<unknown>;
  on?: (event: string, handler: (accounts: string[]) => void) => void;
  removeListener?: (event: string, handler: (accounts: string[]) => void) => void;
};

declare global {
  interface Window {
    ethereum?: EthereumProvider;
  }
}

type WalletContextValue = {
  wallet: string;
  token: string;
  isIssuer: boolean;
  isAdmin: boolean;
  loading: boolean;
  connectAndSignIn: () => Promise<void>;
  sendTransaction: (transaction: ChainTransaction) => Promise<string>;
  signOut: () => void;
};

const WalletContext = createContext<WalletContextValue | null>(null);

export function WalletProvider({ children }: { children: ReactNode }) {
  const [wallet, setWallet] = useState("");
  const [token, setToken] = useState("");
  const [isIssuer, setIsIssuer] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setWallet(localStorage.getItem("cityu.wallet") ?? "");
    setToken(localStorage.getItem("cityu.token") ?? "");
    setIsIssuer(localStorage.getItem("cityu.isIssuer") === "true");
    setIsAdmin(localStorage.getItem("cityu.isAdmin") === "true");
  }, []);

  const signOut = useCallback(() => {
    setWallet("");
    setToken("");
    setIsIssuer(false);
    setIsAdmin(false);
    localStorage.removeItem("cityu.wallet");
    localStorage.removeItem("cityu.token");
    localStorage.removeItem("cityu.isIssuer");
    localStorage.removeItem("cityu.isAdmin");
  }, []);

  useEffect(() => {
    const provider = window.ethereum;
    if (!provider?.on) return;
    const handleAccounts = (accounts: string[]) => {
      if (!accounts[0] || accounts[0].toLowerCase() !== wallet.toLowerCase()) {
        signOut();
      }
    };
    provider.on("accountsChanged", handleAccounts);
    return () => provider.removeListener?.("accountsChanged", handleAccounts);
  }, [signOut, wallet]);

  const connectAndSignIn = useCallback(async () => {
    if (!window.ethereum) throw new Error("Please install MetaMask first.");
    setLoading(true);
    try {
      const accounts = (await window.ethereum.request({
        method: "eth_requestAccounts",
      })) as string[];
      const account = accounts[0];
      if (!account) throw new Error("No wallet account selected.");
      const nonce = await apiFetch<{ message: string }>("/auth/nonce", {
        method: "POST",
        body: JSON.stringify({ wallet_address: account }),
      });
      const signature = (await window.ethereum.request({
        method: "personal_sign",
        params: [nonce.message, account],
      })) as string;
      const auth = await apiFetch<{
        access_token: string;
        wallet_address: string;
        is_issuer: boolean;
        is_admin: boolean;
      }>("/auth/verify", {
        method: "POST",
        body: JSON.stringify({ wallet_address: account, signature }),
      });
      setWallet(auth.wallet_address);
      setToken(auth.access_token);
      setIsIssuer(auth.is_issuer);
      setIsAdmin(auth.is_admin);
      localStorage.setItem("cityu.wallet", auth.wallet_address);
      localStorage.setItem("cityu.token", auth.access_token);
      localStorage.setItem("cityu.isIssuer", String(auth.is_issuer));
      localStorage.setItem("cityu.isAdmin", String(auth.is_admin));
    } finally {
      setLoading(false);
    }
  }, []);

  const sendTransaction = useCallback(
    async (transaction: ChainTransaction) => {
      if (!window.ethereum) throw new Error("Please install MetaMask first.");
      if (!wallet) throw new Error("Connect and sign in with MetaMask first.");
      const chainId = `0x${transaction.chain_id.toString(16)}`;
      await window.ethereum.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId }],
      });
      const accounts = (await window.ethereum.request({
        method: "eth_accounts",
      })) as string[];
      if (!accounts[0] || accounts[0].toLowerCase() !== wallet.toLowerCase()) {
        throw new Error("The active MetaMask account does not match your login wallet.");
      }
      return (await window.ethereum.request({
        method: "eth_sendTransaction",
        params: [
          {
            from: wallet,
            to: transaction.to,
            data: transaction.data,
            value: "0x0",
          },
        ],
      })) as string;
    },
    [wallet],
  );

  const value = useMemo(
    () => ({
      wallet,
      token,
      isIssuer,
      isAdmin,
      loading,
      connectAndSignIn,
      sendTransaction,
      signOut,
    }),
    [
      wallet,
      token,
      isIssuer,
      isAdmin,
      loading,
      connectAndSignIn,
      sendTransaction,
      signOut,
    ],
  );
  return <WalletContext.Provider value={value}>{children}</WalletContext.Provider>;
}

export function useWallet() {
  const context = useContext(WalletContext);
  if (!context) throw new Error("useWallet must be used inside WalletProvider");
  return context;
}
