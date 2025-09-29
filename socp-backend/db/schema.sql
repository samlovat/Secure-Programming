-- SOCP v1.3 Database Schema aligned to §15.1
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY, -- UUID, case-sensitive strings, unique Network-wide
  pubkey TEXT NOT NULL, -- RSA-4096 (base64url)
  privkey_store TEXT NOT NULL, -- Encrypted private key blob
  pake_password TEXT NOT NULL, -- PAKE verifier / salted hash
  meta TEXT, -- Optional decorative fields (JSON)
  version INTEGER NOT NULL DEFAULT 1 -- bumps on deco/security changes
);

-- Groups table (supports both public channel and private groups)
CREATE TABLE IF NOT EXISTS groups (
  group_id TEXT PRIMARY KEY, -- UUID or "public" for public channel
  creator_id TEXT NOT NULL, -- UUID or "system" for public channel
  created_at INTEGER, -- Unix timestamp in milliseconds
  meta TEXT, -- Optional: title, avatar, extras (JSON)
  version INTEGER NOT NULL DEFAULT 1 -- Bumps on membership/key rotation
);

-- Group members table
CREATE TABLE IF NOT EXISTS group_members (
  group_id TEXT NOT NULL, -- UUID or "public" for public channel
  member_id TEXT NOT NULL, -- UUID
  role TEXT, -- "owner" | "admin" | "member", public channel only has "member"
  wrapped_key TEXT NOT NULL, -- RSA-OAEP(SHA-256) of current group_key for member_id
  added_at INTEGER, -- Timestamp of when user was added
  PRIMARY KEY (group_id, member_id)
);

-- Server registry for bootstrap/introducer functionality
CREATE TABLE IF NOT EXISTS servers (
  server_id TEXT PRIMARY KEY, -- UUID
  host TEXT NOT NULL,
  port INTEGER NOT NULL,
  pubkey TEXT NOT NULL, -- RSA-4096 public key (base64url)
  last_seen INTEGER, -- Last heartbeat timestamp
  is_introducer BOOLEAN DEFAULT FALSE
);

-- Bootstrap servers configuration
CREATE TABLE IF NOT EXISTS bootstrap_servers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  host TEXT NOT NULL,
  port INTEGER NOT NULL,
  pubkey TEXT NOT NULL, -- RSA-4096 public key (base64url)
  is_active BOOLEAN DEFAULT TRUE
);
