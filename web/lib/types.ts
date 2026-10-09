export type Traits = Record<string, string>;

export type ChogSummary = { token_id: number; name: string; traits: Traits; image: string | null };

export type Achievement = { slug: string; name: string; icon: string; earned_at?: string; tx?: string | null };

export type ChogProfile = {
  token_id: number;
  collection: string;
  name: string;
  owner: string;
  owner_count: number;
  traits: Traits;
  image: string | null;
  stats: {
    quests_completed: number;
    events_attended: number;
    achievements: number;
    onchain: { quests?: number; events?: number; wins?: number; contributions?: number };
  };
  achievements: Achievement[];
  history: { type: "event" | "achievement"; title: string; at: string }[];
};

export type ChogEvent = {
  id: number;
  slug: string;
  title: string;
  description: string;
  starts_at: string;
  ends_at: string | null;
  kind: string;
  visibility: "public" | "holder";
  official: boolean;
  capacity: number | null;
  participants: number;
  prize: string | null;
  link: string | null;
  joined: boolean;
  quests?: Quest[];
};

export type QuestStatus = "available" | "in_progress" | "submitted" | "approved" | "rejected";

export type Quest = {
  id: number;
  slug: string;
  title: string;
  description: string;
  verify_type: "manual" | "auto_buy" | "auto_event";
  event_id: number | null;
  trait_requirement: Traits | null;
  achievement: Achievement;
  status: QuestStatus;
};

export type ActionCard = {
  id: number;
  kind: "buy_chog";
  status: "prepared" | "sent" | "confirmed" | "failed" | "expired";
  params: { chog_amount: number; mon_cost: number; min_out: number };
  tx: { to: `0x${string}`; data: `0x${string}`; value: string; chainId: number };
  tx_hash: string | null;
  result: { chog_received: number; mon_spent: number } | null;
  expires_at: string;
};

export type ChatMsg = { role: "user" | "assistant"; content: string; actions?: ActionCard[] };

export type PublicConfig = {
  network: string;
  chain_id: number;
  explorer: string;
  chain_mode: "fake" | "web3";
  contracts: Record<"nft" | "token" | "vendor" | "registry", string>;
};
