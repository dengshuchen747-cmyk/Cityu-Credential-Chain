import { ShareView } from "@/components/share-view";

export default async function SharedCredentialPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <section className="page-shell share-page"><ShareView token={token} /></section>;
}
