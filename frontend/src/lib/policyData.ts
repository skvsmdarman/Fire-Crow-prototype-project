export interface PolicySection {
  id: string;
  title: string;
  body: string;
  regions: ("global" | "in" | "eu" | "us")[]; // regions this clause applies to
}

export const TERMS_SECTIONS: PolicySection[] = [
  // --- Core Global SaaS Clauses ---
  {
    id: "license-grant",
    title: "1. License Grant & Scope of Service",
    body: "FireCrow grants you a non-exclusive, non-transferable, non-sublicensable, and revocable right to access and use our subscription-based agentic security audit orchestration platform solely for your internal defensive security purposes. This agreement constitutes a subscription service agreement and is not a sale of software. All rights not explicitly granted herein are reserved by Nova Devs.",
    regions: ["global", "in", "eu", "us"]
  },
  {
    id: "user-accounts",
    title: "2. User Accounts & Security",
    body: "To access the platform, you must register a workspace account. You are solely responsible for maintaining the confidentiality of your account credentials, passwords, and API tokens. You agree to notify us immediately of any unauthorized access. Nova Devs is not liable for any losses caused by unauthorized use of your account, and you may be held liable for activities occurring under your credentials.",
    regions: ["global", "in", "eu", "us"]
  },
  {
    id: "acceptable-use",
    title: "3. Acceptable Use Policy (AUP)",
    body: "You agree not to: (a) engage in any illegal activities or bypass security boundaries; (b) reverse engineer, decompile, or disassemble the platform or backend code; (c) scrape, mine, or copy content from the service without authorization; (d) upload or transmit malware, viruses, or malicious payloads; (e) submit target repositories, endpoints, or environments for which you do not have explicit, written authorization to perform security testing.",
    regions: ["global", "in", "eu", "us"]
  },
  {
    id: "intellectual-property",
    title: "4. Intellectual Property (IP) Ownership",
    body: "Nova Devs (and its licensors) retains all right, title, and interest in and to the platform, including source code, UI designs, underlying agent architectures, database schemas, and pre-existing intellectual property. You (the Customer) retain exclusive ownership of all source code, manifests, and data uploaded or linked to the platform ('Customer Data'). You grant FireCrow a limited license to process Customer Data solely to perform the requested security audit.",
    regions: ["global", "in", "eu", "us"]
  },
  {
    id: "sla-uptime",
    title: "5. Service Level Agreement (SLA)",
    body: "Nova Devs endeavors to maintain a service uptime of 99.9% during each monthly billing cycle, excluding scheduled maintenance. In the event of a verified breach of this uptime guarantee, your sole and exclusive remedy is the issuance of service credits equivalent to 10% of the monthly subscription fee for each hour of cumulative downtime, capped at 100% of the monthly fee. Credits must be requested within 30 days of the incident.",
    regions: ["global", "in", "eu", "us"]
  },
  {
    id: "termination-clause",
    title: "6. Termination & Data Export Protocols",
    body: "Either party may terminate this agreement for convenience upon 30 days' written notice, or immediately for cause if the other party breaches a material provision. Upon termination, your right to access the platform ceases immediately. Within 30 days of termination, you may request a compressed export of your historical audit reports and findings. After 30 days, all Customer Data and associated audit history will be permanently deleted from our databases (including Neon DB and storage buckets) in accordance with our retention policy.",
    regions: ["global", "in", "eu", "us"]
  },
  {
    id: "limitation-liability",
    title: "7. Limitation of Liability",
    body: "TO THE MAXIMUM EXTENT PERMITTED BY LAW, IN NO EVENT SHALL NOVA DEVS BE LIABLE FOR ANY CONSEQUENTIAL, INDIRECT, SPECIAL, PUNITIVE, OR INCIDENTAL DAMAGES (INCLUDING LOSS OF PROFITS, DATA CORRUPTION, OR BUSINESS INTERRUPTION). OUR CUMULATIVE LIABILITY ARISING OUT OF OR IN CONNECTION WITH THIS AGREEMENT SHALL BE STRICTLY CAPPED AT THE TOTAL AMOUNT ACTUALLY PAID BY YOU TO NOVA DEVS FOR THE SERVICES IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM.",
    regions: ["global", "in", "eu", "us"]
  },

  // --- India-Specific Clauses (DPDP Act 2023 & IT Act) ---
  {
    id: "india-roles",
    title: "8. Data Fiduciary & Processor Roles (India DPDP compliance)",
    body: "For the purposes of the Digital Personal Data Protection (DPDP) Act, 2023, the Customer acts as the 'Data Fiduciary' who determines the purpose and means of processing personal data, and Nova Devs acts as the 'Data Processor' processing such data solely on behalf of, and according to the instructions of, the Data Fiduciary.",
    regions: ["in"]
  },
  {
    id: "india-purpose-limitation",
    title: "9. Purpose Limitation & Data Minimization",
    body: "Nova Devs processes personal data only for the specific, limited purpose of providing repository security audit orchestration, dynamic testing, and vulnerability reporting. We do not process personal data for any secondary or unrelated purposes without the explicit instructions of the Data Fiduciary.",
    regions: ["in"]
  },
  {
    id: "india-consent",
    title: "10. Consent & Notice Requirements",
    body: "The Data Fiduciary warrants and represents that 'freely given, specific, informed, and unconditional' consent has been obtained from all data subjects whose personal data is uploaded or processed within the platform, and that the notice of processing has been provided in accordance with Section 5 of the DPDP Act, 2023.",
    regions: ["in"]
  },
  {
    id: "india-breach-notification",
    title: "11. Mandatory Data Breach Notification",
    body: "In the event of a personal data breach or security incident affecting your workspace, Nova Devs will notify the Data Fiduciary immediately. The Data Fiduciary acknowledges its obligation to report such breach to the Data Protection Board of India (DPBI) and the affected users as mandated by the DPDP Act, 2023.",
    regions: ["in"]
  },
  {
    id: "india-grievance",
    title: "12. Grievance Redressal Officer",
    body: "If you are a user in India and have any grievances, complaints, or questions regarding personal data processing, you may contact our designated Grievance Officer: Grievance Officer, Nova Devs Security Group, Email: security@novadevs.dev. We commit to acknowledging your grievance within 24 hours and resolving it within the statutory period of 15 days.",
    regions: ["in"]
  },

  // --- Europe-Specific Clauses (GDPR & AI Act) ---
  {
    id: "eu-dpa",
    title: "13. Data Processing Addendum (DPA) & Right to Audit",
    body: "This agreement incorporates our standard Data Processing Addendum (DPA). Customers have the right to audit our data protection compliance once per calendar year upon reasonable notice. Audits will be conducted during normal business hours and must not disrupt platform operations. The customer bears the cost of the audit.",
    regions: ["eu"]
  },
  {
    id: "eu-subprocessors",
    title: "14. Sub-processors and Consent",
    body: "Nova Devs engages third-party sub-processors (including hosting services, Neon database provider, and R2/S3 storage providers) to deliver the service. A complete list of current sub-processors is available in our DPA. We will provide 30 days' advance notice of any additions or replacements of sub-processors, giving you the right to object in writing on reasonable privacy grounds.",
    regions: ["eu"]
  },
  {
    id: "eu-subject-rights",
    title: "15. Data Subject Rights Assistance",
    body: "Under the GDPR, European users have the right to access, rectify, port, restrict processing of, and erase ('Right to be Forgotten') their personal data. As a Data Processor, Nova Devs will assist the Customer (Data Controller) in responding to data subject requests within 3 business days by providing tools to export or permanently delete user data.",
    regions: ["eu"]
  },
  {
    id: "eu-cross-border",
    title: "16. Cross-Border Data Transfers & SCCs",
    body: "If personal data originating in the European Economic Area (EEA) is transferred to or processed in a country outside the EEA that lacks an adequacy decision, such transfers are governed by the European Commission's Standard Contractual Clauses (SCCs), which are incorporated into our DPA by reference.",
    regions: ["eu"]
  },
  {
    id: "eu-ai-transparency",
    title: "17. AI Transparency & Scoring Disclosure (EU AI Act)",
    body: "In compliance with the EU AI Act, we disclose that FireCrow utilizes artificial intelligence models (specifically the Gemini LLM) in the scoring and analysis phase to deduplicate vulnerabilities, identify exploit paths, and compile remediation advice. By initiating an audit, you acknowledge and consent to the use of AI tools for generating security findings.",
    regions: ["eu"]
  },

  // --- USA-Specific Clauses (CCPA/CPRA & State Laws) ---
  {
    id: "us-ccpa-provider",
    title: "18. CCPA/CPRA Service Provider Certification",
    body: "Nova Devs acts as a 'Service Provider' under the California Consumer Privacy Act (CCPA) as amended by the CPRA. We certify that we will not sell or 'share' (for cross-context behavioral advertising) customer personal information. We will not retain, use, or disclose personal information for any purpose other than performing the business services specified in this contract.",
    regions: ["us"]
  },
  {
    id: "us-opt-out",
    title: "19. Consumer Opt-Out Rights",
    body: "California and US state laws grant residents rights regarding their personal data, including the right to opt out of the sale or sharing of information. While FireCrow does not sell or share your data, we provide a unified toggle to restrict all non-essential data telemetry in your account settings.",
    regions: ["us"]
  },
  {
    id: "us-warranty-disclaimer",
    title: "20. Capitalized Warranty Disclaimers (UCC Standards)",
    body: "THE PLATFORM IS PROVIDED ON AN 'AS IS' AND 'AS AVAILABLE' BASIS. TO THE MAXIMUM EXTENT PERMITTED BY LAW, NOVA DEVS DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT. WE DO NOT WARRANT THAT THE PLATFORM WILL BE UNINTERRUPTED, SECURE, OR COMPLETELY FREE OF ERRORS OR VULNERABILITIES.",
    regions: ["us"]
  },
  {
    id: "us-dispute-resolution",
    title: "21. Binding Arbitration & Class Action Waiver",
    body: "ALL DISPUTES ARISING UNDER THIS AGREEMENT SHALL BE RESOLVED BY INDIVIDUAL BINDING ARBITRATION UNDER THE JAMS SIMPLIFIED ARBITRATION RULES. YOU AND NOVA DEVS AGREE TO WAIVE ANY RIGHT TO A JURY TRIAL AND AGREE THAT ANY CLAIMS MUST BE BROUGHT IN AN INDIVIDUAL CAPACITY AND NOT AS A PLAINTIFF OR CLASS MEMBER IN ANY PURPORTED CLASS OR REPRESENTATIVE PROCEEDING.",
    regions: ["us"]
  },
  {
    id: "us-government-users",
    title: "22. US Government End Users",
    body: "The platform and associated documentation are 'Commercial Computer Software' and 'Commercial Computer Software Documentation' under FAR 12.212 and DFARS 227.7202. Any use, modification, reproduction, release, performance, display, or disclosure by the US Government is governed solely by the terms of this agreement and is prohibited except to the extent expressly permitted.",
    regions: ["us"]
  }
];

export const PRIVACY_SECTIONS: PolicySection[] = [
  {
    id: "policy-intro",
    title: "1. Scope & Core Principles",
    body: "This Privacy Policy describes how FireCrow collects, uses, and discloses information in connection with our agentic security orchestration platform. We are committed to processing data strictly to perform authorized repository scans, manage authentication states, and comply with international regulations including DPDP Act (India), GDPR (Europe), and CCPA (USA).",
    regions: ["global", "in", "eu", "us"]
  },
  {
    id: "data-collection",
    title: "2. Types of Data We Process",
    body: "We process: (a) account identifiers (emails, hashed credentials, workspace names); (b) audit targets (repository URLs, branch names, code manifests); (c) security findings (secrets, dependency reports, vulnerability code snippets); (d) legal consents (notice click timestamps, IP addresses, timezone options, and browser user-agents recorded in Neon DB to preserve a compliance log).",
    regions: ["global", "in", "eu", "us"]
  },
  {
    id: "data-use",
    title: "3. Purpose and Legal Basis",
    body: "We process data solely to execute the authorized scanners, scoring models, and report generation requested by the workspace administrator. Depending on your region, processing is based on contractual necessity, explicit consent, or legitimate interest in defending your codebase from security risks.",
    regions: ["global", "in", "eu", "us"]
  },
  {
    id: "retention-policy",
    title: "4. Storage and Data Retention",
    body: "Audit logs, code manifests, and findings are stored in secure Neon PostgreSQL and Cloudflare R2 storage. All local temporary reports are purged from local filesystems immediately after email transmission. Historical audit records are retained for the active duration of your subscription and permanently deleted within 30 days of subscription termination.",
    regions: ["global", "in", "eu", "us"]
  },
  {
    id: "india-dpdp-rights",
    title: "5. DPDP Act Rights & Grievance officer (India)",
    body: "Under India's DPDP Act 2023, you have rights to access summaries of processed data, seek correction or erasure, and register grievances. Consent can be withdrawn at any time. For concerns, write to security@novadevs.dev. Grievance complaints will be acknowledged in 24 hours and addressed within 15 days.",
    regions: ["in"]
  },
  {
    id: "eu-gdpr-rights",
    title: "6. GDPR Rights, Auditing, & Sub-processors (Europe)",
    body: "Under GDPR, EEA residents have the right to object to processing, request portability, rectify information, and demand erasure ('Right to be Forgotten'). We maintain standard contractual clauses (SCCs) for cross-border transfers and maintain a dynamic list of approved sub-processors. You have a right to audit our compliance once per year.",
    regions: ["eu"]
  },
  {
    id: "us-ccpa-rights",
    title: "7. California & US State Privacy Rights (CCPA/CPRA)",
    body: "California residents have the right to request disclosure of categories of personal information collected, the business purpose, and the right to delete. Nova Devs operates as a 'Service Provider' and certifies that it does not sell or share personal information for cross-context advertising. We honor opt-out configurations.",
    regions: ["us"]
  }
];

export interface RegionOption {
  code: "global" | "in" | "eu" | "us";
  name: string;
  flag: string;
  badge: string;
}

export const REGION_OPTIONS: RegionOption[] = [
  { code: "global", name: "Global / Standard", flag: "🌍", badge: "Universal" },
  { code: "in", name: "India", flag: "🇮🇳", badge: "DPDP Act Compliant" },
  { code: "eu", name: "Europe", flag: "🇪🇺", badge: "GDPR & AI Act Compliant" },
  { code: "us", name: "United States", flag: "🇺🇸", badge: "CCPA & UCC Compliant" }
];

export function detectRegionFromTimezone(timezone?: string): "global" | "in" | "eu" | "us" {
  const tz = timezone || (typeof Intl !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : "") || "";
  const tzLower = tz.toLowerCase();
  
  if (tzLower.includes("kolkata") || tzLower.includes("calcutta") || tzLower.includes("asia/india")) {
    return "in";
  }
  if (
    tzLower.includes("europe/") ||
    tzLower.includes("london") ||
    tzLower.includes("paris") ||
    tzLower.includes("berlin") ||
    tzLower.includes("rome") ||
    tzLower.includes("madrid") ||
    tzLower.includes("dublin") ||
    tzLower.includes("brussels") ||
    tzLower.includes("warsaw") ||
    tzLower.includes("amsterdam") ||
    tzLower.includes("stockholm") ||
    tzLower.includes("helsinki") ||
    tzLower.includes("oslo") ||
    tzLower.includes("copenhagen") ||
    tzLower.includes("vienna") ||
    tzLower.includes("athens") ||
    tzLower.includes("lisbon") ||
    tzLower.includes("prague") ||
    tzLower.includes("budapest") ||
    tzLower.includes("zurich") ||
    tzLower.includes("geneva")
  ) {
    return "eu";
  }
  if (
    tzLower.includes("america/") ||
    tzLower.includes("us/") ||
    tzLower.includes("hawaii") ||
    tzLower.includes("alaska") ||
    tzLower.includes("pacific/") ||
    tzLower.includes("mountain/") ||
    tzLower.includes("central/") ||
    tzLower.includes("eastern/")
  ) {
    return "us";
  }
  
  return "global";
}
