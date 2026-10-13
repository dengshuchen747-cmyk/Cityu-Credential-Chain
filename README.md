# CityU Credential Chain

A university activity credential platform for CityU. Schools issue non-transferable Soulbound Tokens (SBTs), students collect them in their wallets, and enterprises view verified experiences by wallet address.

The prototype uses Ethereum Sepolia. Only authorized issuers can issue or revoke credentials; public viewers have read-only access.

## About

Traditional activity certificates are usually issued as paper documents or editable PDF files. They can be difficult for employers to verify, easy to lose, and costly for universities to manage. CityU Credential Chain provides a blockchain-based way to issue, preserve, and verify university activity credentials.

The project follows one simple principle: **only an authorized university issuer can create or revoke a credential, while students and third parties can independently view and verify it.** Each approved achievement is represented by a non-transferable Soulbound Token (SBT), so it cannot be sold or transferred to another wallet.

The application separates private workflow data from public proof. Student contact details and evidence files stay off-chain in the university backend. The final credential hash, issuer, owner, token ID, metadata URI, and revocation state are recorded on Ethereum Sepolia. An optional IPFS URI can be attached for public credential metadata without exposing private evidence.

This gives the platform the complete credential lifecycle: **publishing activities, collecting evidence, reviewing applications, issuing SBTs, revoking credentials, and verifying student experiences.**

## Technical Insight

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Blockchain | [Ethereum Sepolia](https://ethereum.org/), Solidity 0.8.24, OpenZeppelin | Stores credential ownership, issuer identity, data hashes, metadata URIs, and revocation state. |
| Smart-contract workflow | Remix IDE + VS Code | Compiles, tests, deploys, and verifies the contracts without Hardhat or Truffle. |
| Wallet and signing | [MetaMask](https://metamask.io/) | Connects administrator, issuer, and student wallets. Authorized users sign role, issuance, and revocation transactions in the browser. |
| Backend | Python, [FastAPI](https://fastapi.tiangolo.com/), Web3.py | Provides APIs for campaigns, claims, role checks, transaction preparation, confirmation, and public credential lookup. |
| Persistence | SQLAlchemy + MySQL | Stores campaigns, applications, review status, evidence references, transaction records, and audit data. |
| Frontend | [Next.js](https://nextjs.org/) + React + TypeScript | Provides the school, student, and enterprise interfaces. |
| Public metadata | Optional IPFS URI | Links a credential to public decentralized metadata; private student evidence is not uploaded automatically. |

The Solidity logic is split into `UniCredentialSBT` and `DisclosureRegistry` instead of one oversized contract. This keeps each deployable contract below Ethereum's 24,576-byte runtime code-size limit and makes the credential and disclosure responsibilities easier to maintain. The current enterprise lookup uses public, read-only credential data and does not grant modification rights.

## Project Structure

```text
Cityu-Credential-Chain/
├── README.md                         # Project overview and demo
├── compose.yaml                      # Local MySQL service
├── deployments/
│   └── sepolia.example.json          # Sepolia deployment template
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI application entry point
│   │   ├── core/
│   │   │   ├── config.py             # Environment-based configuration
│   │   │   └── database.py           # SQLAlchemy engine and sessions
│   │   ├── models/
│   │   │   └── entities.py           # Campaign, claim, credential, and audit models
│   │   ├── routers/
│   │   │   ├── admin.py              # Administrator role management
│   │   │   ├── auth.py               # Wallet authentication
│   │   │   ├── campaigns.py          # Activity publishing and discovery
│   │   │   ├── claims.py             # Evidence submission and review
│   │   │   └── credentials.py        # Issuance, revocation, and verification APIs
│   │   ├── services/
│   │   │   ├── blockchain.py         # Sepolia and contract integration
│   │   │   ├── credential_hash.py    # Canonical credential hashing
│   │   │   ├── storage.py            # Private evidence storage
│   │   │   └── auth.py               # Wallet signature validation
│   │   ├── schemas/
│   │   │   └── api.py                # Pydantic request and response schemas
│   │   └── contracts/
│   │       └── UniCredentialSBT.abi.json
│   ├── scripts/
│   │   ├── init_db.py                # MySQL table initialization
│   │   └── reconcile_credentials.py  # Recover confirmed on-chain records
│   ├── tests/                         # FastAPI and service tests with pytest
│   ├── .env.example                  # Backend environment template
│   └── requirements.txt              # Python dependencies
├── frontend/
│   ├── app/
│   │   ├── page.tsx                  # Public CityU activity feed
│   │   ├── school/                   # Administrator and activity creator pages
│   │   ├── student/                  # Student application and SBT wallet
│   │   └── enterprise/               # Public student experience lookup
│   ├── components/                   # Wallet, campaign, dashboard, and lookup UI
│   ├── lib/                          # API client and shared TypeScript types
│   ├── .env.local.example            # Frontend environment template
│   └── package.json                  # Next.js dependencies and scripts
├── remix/
│   ├── contracts/
│   │   ├── UniCredentialSBT.sol      # Non-transferable credential contract
│   │   ├── DisclosureRegistry.sol    # Optional disclosure authorization registry
│   │   └── interfaces/               # Shared Solidity interfaces
│   ├── tests/                         # Solidity tests for Remix
│   └── scripts/
│       └── verify-contracts.mjs       # Contract verification helper
├── docs/
│   └── images/                        # README demo screenshots
└── remix.config.json                 # Remix compiler and optimizer configuration
```

## Role Model

| Entry | Role |
| --- | --- |
| School — Administrator | Manage who can create activities and issue credentials. |
| School — Activity Creator | Publish activities, review applications, and issue or revoke SBTs. |
| Student | Submit participation evidence, track applications, and view owned SBTs. |
| Enterprise | Enter a student wallet address to view public CityU credentials and their current validity. |

The administrator role is part of the intended design. The screenshots below show the activity creator, student, and enterprise workflows.

## Functions

### 1. CityU Activity Feed

Browse published CityU activities, read participation requirements, and apply for a credential.

![Published CityU activities](docs/images/demo-03.png)

### 2. Activity Creation

Create an activity with a title, credential type, description, claim limit, and optional public IPFS metadata URI.

![Activity creation form](docs/images/demo-02.png)

<details>
<summary>Additional activity creation screenshot</summary>

![Activity creation form with claim limit](docs/images/demo-01.png)

</details>

### 3. Credential Applications

Connect a student wallet and submit participation evidence as a PDF, JPG, or PNG. Evidence files remain private; their hash provides a link to the credential proof.

![Student credential application](docs/images/demo-04.png)

### 4. Application Review

Activity creators approve or reject student claims. Approval and on-chain issuance are separate steps.

![Pending student claims with approve and reject actions](docs/images/demo-06.png)

### 5. SBT Issuance

Issue approved credentials through MetaMask and wait for the Sepolia transaction to confirm.

![Approved claims and MetaMask SBT issuance](docs/images/demo-07.png)

### 6. Student Credential Wallet

Track application status and view owned SBTs, including the issuer, token ID, issue date, validity, and transaction link. Credentials cannot be transferred between wallets.

![Student wallet containing issued CityU SBTs](docs/images/demo-09.png)

<details>
<summary>Additional student wallet screenshots</summary>

**Pending applications**

![Student wallet with pending applications](docs/images/demo-05.png)

**Approved applications awaiting issuance**

![Student wallet with approved applications and no issued SBTs yet](docs/images/demo-08.png)

**Credential details**

![Issued credential details and transaction links](docs/images/demo-10.png)

**Wallet overview**

![Student wallet overview with three owned SBTs](docs/images/demo-12.png)

</details>

### 7. On-Chain Transaction Records

Open the credential transaction on Sepolia Etherscan to inspect its minting record, issuer, recipient, and confirmation status.

![Successful CityU credential mint on Sepolia Etherscan](docs/images/demo-11.png)

### 8. Enterprise Experience Lookup

Enter a student wallet address to view all CityU SBTs held by that wallet and their current on-chain validity. No login or student approval is required. This read-only view shows public credential facts while keeping evidence files and contact details private.

![Enterprise lookup showing verified CityU experiences](docs/images/demo-13.png)
